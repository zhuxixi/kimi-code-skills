#Requires -Version 5.1
<#
.SYNOPSIS
    Safely stops a process listening on a specific port.
.DESCRIPTION
    Finds the process listening on the specified port and terminates it.
    Excludes the current PowerShell process to prevent self-termination.
.PARAMETER Port
    The port number to search for.
.PARAMETER Force
    Forcefully terminate the process.
.EXAMPLE
    .\stop-server-on-port.ps1 -Port 3000
    Stops the process listening on port 3000.
#>
param(
    [Parameter(Mandatory=$true)]
    [int]$Port,
    
    [switch]$Force
)

$myPid = $PID
$found = $false

Write-Host "Searching for process on port $Port..." -ForegroundColor Cyan

# Get netstat output and parse
$connections = netstat -ano | findstr ":$Port " | findstr "LISTENING"

if (-not $connections) {
    Write-Host "No process found listening on port $Port" -ForegroundColor Yellow
    exit 0
}

foreach ($line in $connections) {
    $parts = $line -split '\s+' | Where-Object { $_ }
    
    if ($parts.Count -ge 5) {
        $localAddress = $parts[1]
        $targetPid = $parts[4]
        
        # Safety check: don't kill self
        if ($targetPid -eq $myPid) {
            Write-Host "Skipping own process (PID: $myPid)" -ForegroundColor Yellow
            continue
        }
        
        try {
            $process = Get-Process -Id $targetPid -ErrorAction Stop
            $found = $true
            
            Write-Host "Found process:" -ForegroundColor Green
            Write-Host "  PID: $($process.Id)" -ForegroundColor White
            Write-Host "  Name: $($process.ProcessName)" -ForegroundColor White
            Write-Host "  Port: $Port" -ForegroundColor White
            
            if ($Force) {
                Stop-Process -Id $targetPid -Force -ErrorAction Stop
                Write-Host "  Status: Terminated" -ForegroundColor Red
            } else {
                Write-Host "  Status: Found (use -Force to terminate)" -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "Error processing PID $targetPid`: $_" -ForegroundColor Red
        }
    }
}

if (-not $found) {
    Write-Host "No eligible processes found to terminate" -ForegroundColor Yellow
}
