@echo off
cd /d "%~dp0..\..\..\.."
"D:\anaconda3\python.exe" "%~dp0..\..\..\..\launch_supplement.py"
if errorlevel 1 pause
