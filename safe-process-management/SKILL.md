---
name: safe-process-management
description: Safe process management on Windows to avoid self-termination. Use when executing process management commands like taskkill, Stop-Process, Get-Process, netstat, or any operation that involves killing, terminating, or managing system processes. Critical for preventing accidental self-termination of Kimi Code CLI or other essential processes.
---

# Safe Process Management

Guidelines for safely managing Windows processes without terminating Kimi Code CLI itself or other critical processes.

## The Risk

Kimi Code CLI runs on Node.js. Blindly killing all `node.exe` processes will terminate Kimi itself, causing immediate session failure.

## Safe Practices

### 1. Identify Before Killing

Always identify the specific target process before termination:

```powershell
# Find process by port (recommended)
netstat -ano | findstr ":<PORT>"

# Find process by name with details
Get-Process node | Select-Object Id, ProcessName, Path

# Find process by command line
Get-WmiObject Win32_Process -Filter "name='node.exe'" | Select-Object ProcessId, CommandLine
```

### 2. Use PID-Based Termination

Always prefer PID-based termination over name-based:

```powershell
# ✅ GOOD - Specific PID
Stop-Process -Id <PID> -Force

# ❌ DANGEROUS - Kills all node.exe including Kimi
taskkill /F /IM node.exe
Stop-Process -Name node -Force
```

### 3. Exclude Self When Bulk Operations Needed

If you must operate on multiple processes, exclude your own PID:

```powershell
# Get current PowerShell/Node process ID
$myPid = $PID

# Kill other node processes except self
Get-Process node | Where-Object { $_.Id -ne $myPid } | Stop-Process -Force
```

### 4. Port-Based Management (Safest)

When managing development servers, use port instead of process name:

```powershell
# Find and kill process using specific port
$port = 3000
$connection = netstat -ano | findstr ":$port " | findstr "LISTENING"
if ($connection) {
    $pid = ($connection -split '\s+')[-1]
    if ($pid -and $pid -ne $PID) {
        Stop-Process -Id $pid -Force
    }
}
```

### 5. Verification Steps

Before executing kill commands:

1. **Check what will be affected**: `Get-Process <name>`
2. **Confirm not self**: Compare PID with `$PID`
3. **Prefer targeted approaches**: Port > Command Line > PID > Name

### 6. Safe Server Management Patterns

```powershell
# Pattern 1: Start and track PID for later termination
$process = Start-Process node -ArgumentList "server.js" -PassThru
# Later: Stop-Process -Id $process.Id -Force

# Pattern 2: Use job control
$job = Start-Job { & npm run dev }
# Later: Stop-Job $job; Remove-Job $job

# Pattern 3: Port-based cleanup (safest)
function Stop-ServerOnPort($port) {
    $lines = netstat -ano | findstr ":$port " | findstr "LISTENING"
    foreach ($line in $lines) {
        $parts = $line -split '\s+' | Where-Object { $_ }
        if ($parts.Count -ge 5) {
            $targetPid = $parts[4]
            if ($targetPid -ne $PID) {
                Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            }
        }
    }
}
```

## Common Pitfalls

| Command | Risk Level | Why |
|---------|-----------|-----|
| `taskkill /F /IM node.exe` | 🔴 HIGH | Kills all Node processes including Kimi |
| `Stop-Process -Name node` | 🔴 HIGH | Same as above |
| `killall node` (WSL) | 🔴 HIGH | Affects WSL Node processes |
| `Stop-Process -Id <PID>` | 🟢 LOW | Targeted, safe if PID correct |
| Port-based termination | 🟢 LOW | Safest approach |

## Emergency Recovery

If you accidentally terminate yourself:
- The session will immediately end
- User will need to restart Kimi Code CLI
- No recovery possible from within the terminated session

## Remember

> **When in doubt, use port-based targeting or PID-specific termination. Never use broad process name matching for Node.js processes.**
