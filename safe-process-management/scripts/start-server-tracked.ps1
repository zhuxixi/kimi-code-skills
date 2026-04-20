#Requires -Version 5.1
<#
.SYNOPSIS
    Starts a server process and tracks its PID for safe termination later.
.DESCRIPTION
    Starts a server process (like npm run dev, python http.server, etc.) in the background
    and outputs a tracking file containing the PID for safe termination.
.PARAMETER Command
    The command to execute (e.g., "npm", "python").
.PARAMETER Arguments
    Arguments for the command (e.g., "run dev", "-m http.server 8080").
.PARAMETER WorkingDirectory
    Working directory for the process.
.PARAMETER Port
    Optional port number to verify the server started.
.PARAMETER Timeout
    Seconds to wait for port to become active (default: 10).
.EXAMPLE
    .\start-server-tracked.ps1 -Command "npm" -Arguments "run dev" -Port 3000
    Starts npm dev server and tracks its PID.
.EXAMPLE
    .\start-server-tracked.ps1 -Command "python" -Arguments "-m http.server 8080" -Port 8080
    Starts Python HTTP server on port 8080.
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$Command,
    
    [string]$Arguments = "",
    
    [string]$WorkingDirectory = ".",
    
    [int]$Port = 0,
    
    [int]$Timeout = 10
)

$pidFile = ".server.pid"
$logFile = ".server.log"

# Check if a server is already running on the port
if ($Port -gt 0) {
    $existing = netstat -ano | findstr ":$Port " | findstr "LISTENING"
    if ($existing) {
        Write-Warning "Port $Port is already in use. Server may already be running."
        exit 1
    }
}

Write-Host "Starting server: $Command $Arguments" -ForegroundColor Cyan
Write-Host "Working directory: $WorkingDirectory" -ForegroundColor Gray

# Start the process
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $Command
$psi.Arguments = $Arguments
$psi.WorkingDirectory = $WorkingDirectory
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi

# Set up output logging
$stdout = $process.StandardOutput
$stderr = $process.StandardError

# Start process
$started = $process.Start()

if (-not $started) {
    Write-Error "Failed to start process"
    exit 1
}

$processId = $process.Id

# Save PID to file
$processId | Out-File -FilePath $pidFile -Encoding utf8 -Force
Write-Host "Server started with PID: $processId" -ForegroundColor Green
Write-Host "PID saved to: $pidFile" -ForegroundColor Gray

# Wait for port to become active if specified
if ($Port -gt 0) {
    Write-Host "Waiting for port $Port to become active..." -ForegroundColor Yellow -NoNewline
    $elapsed = 0
    $started = $false
    
    while ($elapsed -lt $Timeout) {
        $check = netstat -ano | findstr ":$Port " | findstr "LISTENING"
        if ($check) {
            $started = $true
            break
        }
        Start-Sleep -Milliseconds 500
        $elapsed += 0.5
        Write-Host "." -ForegroundColor Yellow -NoNewline
    }
    Write-Host ""
    
    if ($started) {
        Write-Host "Server is ready on port $Port" -ForegroundColor Green
    } else {
        Write-Warning "Server did not start on port $Port within $Timeout seconds"
    }
}

Write-Host ""
Write-Host "To stop the server, run:" -ForegroundColor Cyan
Write-Host "  Stop-Process -Id $processId -Force" -ForegroundColor White
Write-Host "Or use:" -ForegroundColor Cyan
Write-Host "  .\stop-server-tracked.ps1" -ForegroundColor White

# Detach process
$process = $null
