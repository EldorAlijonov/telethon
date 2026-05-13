$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\EldorAlijonov\AppData\Local\Programs\Python\Python313\python.exe"
$PidFile = Join-Path $Root "bot.pid"
$LogFile = Join-Path $Root "bot.log"
$ErrFile = Join-Path $Root "bot.err.log"

if (Test-Path $PidFile) {
    $OldPid = Get-Content $PidFile
    $OldProcess = Get-Process -Id $OldPid -ErrorAction SilentlyContinue
    if ($OldProcess) {
        Stop-Process -Id $OldPid -Force
        Start-Sleep -Seconds 2
    }
}

Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match "python|py" -and $_.CommandLine -match "main\.py" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Remove-Item $LogFile, $ErrFile -ErrorAction SilentlyContinue

$Process = Start-Process `
    -FilePath $Python `
    -ArgumentList "main.py" `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError $ErrFile `
    -PassThru

Set-Content -LiteralPath $PidFile -Value $Process.Id
Start-Sleep -Seconds 8

$Running = Get-Process -Id $Process.Id -ErrorAction SilentlyContinue
if ($Running) {
    Write-Output "RUNNING PID=$($Process.Id)"
    Get-Content $LogFile -ErrorAction SilentlyContinue | Select-Object -Last 20
    Get-Content $ErrFile -ErrorAction SilentlyContinue | Select-Object -Last 20
} else {
    Write-Output "STOPPED"
    Get-Content $ErrFile -ErrorAction SilentlyContinue | Select-Object -Last 120
    exit 1
}
