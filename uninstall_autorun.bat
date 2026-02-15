@echo off
REM Unregisters the scheduled task to stop automatically running the script.
powershell -Command "Unregister-ScheduledTask -TaskName 'WindowPopAlwaysOnTop' -Confirm:$false -ErrorAction SilentlyContinue"
echo Task removed successfully.
pause
