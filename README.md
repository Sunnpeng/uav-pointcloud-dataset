# UAV point-cloud dataset

无人机雷达点云、人工包围盒标注、原始对应 pose 与固定数据划分。处理与标注工具位于 [uav-ugv-offline](https://github.com/Sunnpeng/uav-ugv-offline) 的 `uav-detect`。

## v1.0.0

|类别|帧数|
|---|---:|
|训练集 `train`|1935|
|验证集 `val`|425|
|测试集 `test`|401|
|时间隔离备用 `reserve_temporal_gap`|245|
|10米外补充 `supplement_over10m`|50|
|合计|3056|

主实验范围为0–10米。按20秒连续时间窗分组，跨集合最近时间戳间隔约5.0004秒。训练集覆盖现有数据的8个方位区间；这是同场景、同无人机的时间分组评估，无法代替跨场景测试。

## 获取数据

```bash
git lfs install
git clone https://github.com/Sunnpeng/uav-pointcloud-dataset.git
cd uav-pointcloud-dataset
git lfs pull
python tools/verify_dataset.py
```

PCD与BIN通过Git LFS存储；只下载Git元数据时可在克隆前设置 `GIT_LFS_SKIP_SMUDGE=1`，之后按需执行 `git lfs pull`。

## 文件说明

- 各集合 `pcd/`：原始整帧PCD字节；`cloud/`：四列float32 BIN，XYZ与PCD一致，第4列为0。
- `label/`：`drone cx cy cz dx dy dz [old_yaw]`。新AABB为7字段，有原旧yaw的保留第8字段，不计算或填造yaw。
- `annotations/`：框、姿态原文、来源与最终归属。
- `全部已标注_合并与划分清单.csv`：原始采集ID与帧号唯一键、来源及分组。
- `provenance/annotation_projects/`：三批人工标注JSON原件及分割点云。
- `provenance/source_poses/`：收录帧对应的原始pose行与带时间戳pose行。
- `input_annotation_hashes.json`：人工标注原件及旧标签的SHA-256。

活动清单的 `export_directory`、`label_source`、`target_pcd` 路径以本仓库根目录为基准。历史原始路径仅用于追溯，不要求克隆者具有原机器的D盘目录。

原采集完整rosbag与未收录PCD不包含在此版本；没有原始采集时，标注工具只播放本数据集已保存的帧。历史旧框中心定义与新增AABB中心定义不同，本次发布未自动改写所有旧框。
