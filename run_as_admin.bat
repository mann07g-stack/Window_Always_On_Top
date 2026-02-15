@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    powershell -Command "Start-Process '.venv\Scripts\python.exe' -ArgumentList 'always_on_top.py' -Verb RunAs"
) else (
    powershell -Command "Start-Process 'python' -ArgumentList 'always_on_top.py' -Verb RunAs"
)
