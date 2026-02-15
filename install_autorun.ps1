$TaskName = "WindowPopAlwaysOnTop"
$ScriptPath = "$PSScriptRoot\always_on_top.py"
$PythonPath = "$PSScriptRoot\.venv\Scripts\pythonw.exe"

# 1. Check if running as Admin
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Please run this script as Administrator!" -ForegroundColor Red
    Start-Sleep -Seconds 2
    exit
}

# 2. Check Paths
if (-not (Test-Path $PythonPath)) {
    # Fallback to global pythonw if venv not found
    $PythonPath = "pythonw.exe"
}

# 3. Create Scheduled Task Action
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument """$ScriptPath""" -WorkingDirectory $PSScriptRoot

# 4. Create Trigger (At Logon)
$Trigger = New-ScheduledTaskTrigger -AtLogon

# 5. Create Settings (Allow start if on battery, etc.)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0 -Priority 3

# 6. Register Task
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal (New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest)
    Write-Host "Successfully installed '$TaskName' to run at logon with Admin rights." -ForegroundColor Green
    Write-Host "You can verify this in Task Scheduler."
    
    # Ask to start now
    $response = Read-Host "Start the task now? (Y/N)"
    if ($response -eq 'Y') {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "Task started."
    }
} catch {
    Write-Host "Error registering task: $_" -ForegroundColor Red
}
pause
