"""Independent checks against raw poses, PCD payloads and the actual training loader."""
from pathlib import Path
from collections import defaultdict
import ast,csv,json,hashlib,os
import numpy as np

DATA=Path(__file__).resolve().parents[1]
ROOT=DATA.parents[2]

def data_path(value):
    path=Path(str(value).replace('\\','/'))
    return path if path.is_absolute() else DATA/path

def read(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def pcd_xyz(path):
    with Path(path).open('rb') as f:
        h={}
        while True:
            line=f.readline().decode('ascii').strip().split()
            if not line:continue
            h[line[0]]=line[1:]
            if line[0]=='DATA':break
        fields=h['FIELDS'];sizes=h['SIZE'];types=h['TYPE'];counts=list(map(int,h.get('COUNT',['1']*len(fields))))
        if h['DATA']==['binary']:
            dtype=np.dtype([(name,'<'+{'F':'f','I':'i','U':'u'}[kind]+size) if count==1 else
                            (name,'<'+{'F':'f','I':'i','U':'u'}[kind]+size,(count,))
                            for name,size,kind,count in zip(fields,sizes,types,counts)])
            values=np.frombuffer(f.read(),dtype=dtype)
            xyz=np.stack([values[k] for k in ('x','y','z')],axis=1)
        elif h['DATA']==['ascii']:
            values=np.loadtxt(f,ndmin=2);offsets=np.cumsum([0]+counts[:-1])
            xyz=values[:,[offsets[fields.index(k)] for k in ('x','y','z')]]
        else:raise ValueError('Unexpected compression')
        assert len(xyz)==int(h['POINTS'][0])
        return xyz

def main():
    rows=read(DATA/'全部已标注_合并与划分清单.csv')
    assert len(rows)==3056
    # Load only the actual label-reader function, avoiding training or UI side effects.
    env={'os':os,'np':np}
    loader=ROOT/'uav-detect/training/train_baseline.py'
    if loader.exists():
        module=ast.parse(loader.read_text(encoding='utf-8-sig'))
        fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='load_labels')
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'train_baseline.load_labels','exec'),env)
    else:
        def load_labels(path):
            p=Path(path).read_text().split()
            return [dict(center=np.array(p[1:4],float),size=np.array(p[4:7],float),yaw=float(p[7]) if len(p)>7 else None)]
        env['load_labels']=load_labels
    poses={};timestamps={};seen=set();timegroups=defaultdict(set);timeline=defaultdict(list);clouds=defaultdict(set)
    for seq in sorted({r['sequence'] for r in rows}):
        named=(DATA/'provenance/source_poses'/seq/'poses_named.txt').read_text().splitlines()
        timed=(DATA/'provenance/source_poses'/seq/'poses_timestamped.txt').read_text().splitlines()
        assert len(named)==len(timed)
        poses[seq]={v.split()[0]:v for v in named}
        timestamps[seq]={a.split()[0]:b for a,b in zip(named,timed)}
    for i,r in enumerate(rows):
        key=(r['sequence'],r['file']);assert key not in seen;seen.add(key)
        assert int(r['frame']) not in ({945,947,949} if r['sequence']=='pcd_pose_20250515' else set())
        folder=data_path(r['export_directory']);name=r['id'];frame=int(r['frame'])
        doc=json.loads((folder/'annotations'/f'{name}.json').read_text(encoding='utf-8'))
        assert doc['pose_original_line']==poses[r['sequence']][r['file']]==r['pose_original_line']
        assert doc['pose_with_timestamp_original_line']==timestamps[r['sequence']][r['file']]
        assert doc['yaw_recalculated'] is False
        parsed=env['load_labels'](folder/'label'/f'{name}.txt');assert len(parsed)==1
        assert np.allclose(parsed[0]['center'],doc['center'],atol=1e-8,rtol=0)
        assert np.allclose(parsed[0]['size'],doc['extent'],atol=1e-8,rtol=0)
        if doc['yaw_original_token'] is None:assert parsed[0]['yaw'] is None
        else:assert parsed[0]['yaw']==float(doc['yaw_original_token'])
        pcd=folder/'pcd'/f'{name}.pcd';assert sha(pcd)==r['source_sha256']
        if Path(r['source_pcd']).is_file():assert sha(pcd)==sha(r['source_pcd'])
        assert data_path(r['label_source']).is_file()
        if r.get('target_pcd'):assert data_path(r['target_pcd']).is_file()
        xyz=pcd_xyz(pcd).astype('<f4')
        binary=np.fromfile(folder/'cloud'/f'{name}.bin',dtype='<f4').reshape(-1,4)
        assert np.array_equal(xyz,binary[:,:3]);assert np.all(binary[:,3]==0)
        timegroups[r['time_group']].add(r['split'])
        if r['role']!='时间隔离备用':
            timeline[r['sequence']].append((float(r['timestamp']),r['split']))
            clouds[r['source_sha256']].add(r['split'])
        if r['role']=='主数据0-10m':assert float(r['distance'])<=10
        elif r['role']=='10m外补充':assert float(r['distance'])>10
        if i%1000==0:print(f'Checked {i}/{len(rows)}',flush=True)
    assert all(len(v)==1 for v in timegroups.values())
    assert all(len(v)==1 for v in clouds.values())
    minimum=float('inf')
    for seq,events in timeline.items():
        events.sort()
        for i,(t,s) in enumerate(events):
            for u,other in events[i+1:]:
                if u-t>=5:break
                assert s==other,(seq,t,u,s,other)
        for (t,s),(u,other) in zip(events,events[1:]):
            if s!=other:minimum=min(minimum,u-t)
    assert minimum>=5
    for path,value in json.loads((DATA/'input_annotation_hashes.json').read_text(encoding='utf-8')).items():assert sha(data_path(path))==value
    result=dict(frames_verified=len(rows),raw_pose_rows_exact=True,pcd_bytes_preserved=True,
        bin_xyz_equal_raw_float32=True,training_label_loader_verified=loader.exists(),
        unique_raw_frame_keys=True,cross_split_identical_clouds=0,time_groups_do_not_cross_splits=True,
        minimum_cross_split_gap_seconds=minimum,input_annotations_unchanged=True,yaw_recalculated=False)
    (DATA/'独立核验结果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True,indent=2))

if __name__=='__main__':main()
