@echo off
set "ANNOTATION_PYTHON=python"
if exist "D:\anaconda3\python.exe" set "ANNOTATION_PYTHON=D:\anaconda3\python.exe"
"%ANNOTATION_PYTHON%" "%~dp0..\..\..\..\..\..\scripts\annotate.py" --project repair
if errorlevel 1 pause
