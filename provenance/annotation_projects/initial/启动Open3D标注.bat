@echo off
cd /d "%~dp0..\..\..\.."
"D:\anaconda3\python.exe" "%~dp0..\..\..\..\open3d_launcher.py"
if errorlevel 1 pause
