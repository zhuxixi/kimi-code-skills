#Requires -Version 5.1
<#
.SYNOPSIS
    Stops a server that was started with start-server-tracked.ps1.
.DESCRIPTION
    Reads the PID from .server.pid file and safely terminates the process.
    Includes safety checks to prevent self-termination.
.PARAMETER PidFile
    Path to the PID file (default: .server.pid).
.PARAMETER Force
    Forcefully terminate the process.
#>
param(
    [string]$PidFile = ".server.pid",
    [switch]$Force
)

$myPid = $PID

# Check if PID file exists
if (-not (Test-Path $PidFile)) {
    Write-Warning "PID file not found: $PidFile"
    Write-Host "Server may not be running or was not started with tracking." -ForegroundColor Yellow
    exit 1
}

# Read PID from file
$targetPid = Get-Content $PidFile -Raw
$targetPid = $targetPid.Trim()

if (-not $targetPid) {
    Write-Error "PID file is empty"
    exit 1
}

# Validate PID is numeric
if ($targetPid -notmatch '^\d+$') {
    Write-Error "Invalid PID in file: $targetPid"
    exit 1
}

$targetPid = [int]$targetPid

Write-Host "Target PID: $targetPid" -ForegroundColor Cyan
Write-Host "Current PID: $myPid" -ForegroundColor Gray

# Critical safety check: don't kill self
if ($targetPid -eq $myPid) {
    Write-Error "SAFETY BLOCK: Cannot terminate own process (PID: $myPid)"
    Write-Host "This would terminate the current Kimi Code CLI session." -ForegroundColor Red
    exit 1
}

# Check if process exists
try {
    $process = Get-Process -Id $targetPid -ErrorAction Stop
    Write-Host "Found process: $($process.ProcessName) (PID: $targetPid)" -ForegroundColor Green
    
    if ($Force -or $PSCmdlet.ShouldProcess("PID $targetPid", "Stop Process")) {
        Stop-Process -Id $targetPid -Force -ErrorAction Stop
        Write-Host "Process terminated successfully" -ForegroundColor Green
        
        # Clean up PID file
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        Write-Host "Cleaned up PID file" -ForegroundColor Gray
    }
}
catch [System.Management.Automation.CommandNotFoundException] {
    Write-Error "Process with PID $targetPid not found (may have already exited)"
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}
catch {
    Write-Error "Failed to stop process: $_"
    exit 1
}
