# Vite Dev Server Reliability Investigation & Solutions

**Date**: 2025-11-29  
**Issue**: Vite dev server (localhost:5173) not running after system updates  
**Root Cause**: Vite process terminated (no persistence/auto-restart mechanism)

## Investigation Summary

### Current State
- **Vite Dev UI (Port 5173)**: ❌ STOPPED
- **API (Port 8001)**: ✅ RUNNING (Docker)
- **Frontend (Port 3000)**: ✅ RUNNING (Docker nginx)
- **MySQL, Redis, Qdrant**: ✅ RUNNING (Docker)

### Why Vite Stopped

The Vite dev server was previously running but is **not a persistent service**. Common reasons for termination:

1. **Manual Stop**: User pressed Ctrl+C or closed terminal
2. **System Update**: Windows updates, restarts, or power events
3. **Process Crash**: Uncaught error in Vite or Node.js
4. **Port Conflict**: Another process claimed port 5173
5. **Resource Limits**: Out of memory or file handle exhaustion

**Key Insight**: Unlike Docker services (which auto-restart via `restart: always`), Vite is a **foreground process** that must be manually started and maintained.

## Solutions Implemented

### 1. Service Status Checker (`check_services.ps1`)

**Purpose**: Quick diagnosis of all services

**Usage**:
```powershell
.\scripts\check_services.ps1
```

**Output**:
- ✅/❌ status for Vite, API, MySQL, Redis, Qdrant, Frontend
- Port numbers and URLs
- Docker container count
- Quick action commands

**Reliability Impact**: Immediate visibility into what's running/stopped

---

### 2. Simple Vite Starter (`start_vite.ps1`)

**Purpose**: Quick one-shot Vite startup

**Usage**:
```powershell
.\scripts\start_vite.ps1
```

**Features**:
- Auto-installs dependencies if missing
- Sets `VITE_API_URL` environment variable
- Exits on error (no retry)

**When to Use**: 
- Quick testing
- Debugging (want to see errors immediately)
- One-time development sessions

**Reliability**: ⭐⭐ (no auto-restart)

---

### 3. Persistent Vite Server (`start_vite_persistent.ps1`) ⭐ **RECOMMENDED**

**Purpose**: Long-running Vite with automatic crash recovery

**Usage**:
```powershell
# Unlimited restarts (default)
.\scripts\start_vite_persistent.ps1

# Limit restarts to prevent infinite loops
.\scripts\start_vite_persistent.ps1 -MaxRestarts 10

# Custom API base
.\scripts\start_vite_persistent.ps1 -ApiBase "http://192.168.1.100:8001"
```

**Features**:
- Automatic restart on crashes (with 3-second delay)
- Restart counter and timestamps
- Configurable restart limits
- Detects clean exits (Ctrl+C) vs. crashes
- Informative logging

**When to Use**:
- Development sessions (hours/days)
- CI/CD pipelines
- Demo environments
- When reliability > debugging

**Reliability**: ⭐⭐⭐⭐⭐ (automatic recovery)

**Example Output**:
```
Persistent Vite Server Manager
   API Base: http://localhost:8001
   Max Restarts: Unlimited
   Auto-Restart: Enabled
   Press Ctrl+C to stop

[2025-11-29 14:30:00] Starting Vite (attempt 1)...
  VITE v5.0.0  ready in 823 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h + enter to show help

[2025-11-29 14:35:22] Vite exited with code: 137
Restarting in 3 seconds...

[2025-11-29 14:35:25] Starting Vite (attempt 2)...
```

---

## Reliability Recommendations

### For Development (Local Machine)

**Option A: Manual Start (Current Approach)**
```powershell
# Each session, run:
.\scripts\start_vite_persistent.ps1
```
- ✅ Simple
- ✅ Full control
- ❌ Requires manual action after reboot

**Option B: Windows Scheduled Task (Auto-start on Login)** ⭐ **BEST**
```powershell
# One-time setup:
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -File C:\MySQL\agentic_rag_poc\scripts\start_vite_persistent.ps1"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "RAG-POC Vite Dev" -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings

# To remove:
Unregister-ScheduledTask -TaskName "RAG-POC Vite Dev" -Confirm:$false
```
- ✅ Automatic startup on login
- ✅ Runs in background
- ✅ Survives reboots
- ❌ Harder to see logs (use `Get-EventLog` or file logging)

**Option C: Windows Service (Advanced)**
Use NSSM (Non-Sucking Service Manager) to run Vite as a Windows service:
```powershell
# Install NSSM (one-time)
choco install nssm

# Create service
nssm install RAGPOCVite powershell.exe
nssm set RAGPOCVite AppParameters "-File C:\MySQL\agentic_rag_poc\scripts\start_vite_persistent.ps1"
nssm set RAGPOCVite AppDirectory C:\MySQL\agentic_rag_poc
nssm set RAGPOCVite Start SERVICE_AUTO_START
nssm start RAGPOCVite

# To remove
nssm stop RAGPOCVite
nssm remove RAGPOCVite confirm
```
- ✅ True service (starts before login)
- ✅ Managed via `services.msc`
- ✅ Professional deployment
- ❌ Requires admin rights
- ❌ More complex troubleshooting

---

### For Production/Demo Environments

**Use Containerized Frontend (Port 3000)** instead of Vite dev server:

```powershell
# Already running in your environment!
docker compose up -d frontend

# Access at http://localhost:3000
```

**Why?**
- ✅ Docker handles restart automatically (`restart: always`)
- ✅ Production-optimized build (smaller, faster)
- ✅ No Node.js/npm dependencies on host
- ✅ Survives reboots
- ❌ Requires Docker rebuild on code changes

**When to Use**:
- Production deployments
- Demo servers
- CI/CD test environments
- When uptime > hot-reload

---

## Quick Reference

### Check What's Running
```powershell
.\scripts\check_services.ps1
```

### Start Vite (Simple)
```powershell
.\scripts\start_vite.ps1
```

### Start Vite (Persistent)
```powershell
.\scripts\start_vite_persistent.ps1
```

### Kill Vite Process
```powershell
# Find process on port 5173
$pid = (Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue).OwningProcess
if ($pid) { Stop-Process -Id $pid -Force }
```

### Start All Services
```powershell
docker compose up -d
.\scripts\start_vite_persistent.ps1  # In separate terminal
```

---

## Troubleshooting

### Vite Won't Start (Port Already in Use)

```powershell
# Check what's using port 5173
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | 
    Select-Object State,OwningProcess

# Kill the process
Stop-Process -Id <PID> -Force

# Try again
.\scripts\start_vite.ps1
```

### Vite Crashes Immediately

```powershell
# Run without auto-restart to see error
.\scripts\start_vite.ps1

# Common issues:
# 1. Missing node_modules
cd web
npm install

# 2. Syntax error in vite.config.js
# Check file for errors

# 3. Environment variable issues
$env:VITE_API_URL = "http://localhost:8001"
```

### Can't Access Vite from Another Machine

```powershell
# Vite binds to localhost by default
# Edit web/vite.config.js:
# server: {
#   host: '0.0.0.0',  // Listen on all interfaces
#   port: 5173
# }

# Or use --host flag (not recommended for security)
npm run dev -- --host
```

### Docker Services Won't Start

```powershell
# Check Docker status
docker compose ps

# View logs
docker compose logs mcp
docker compose logs mysql

# Restart all
docker compose down
docker compose up -d
```

---

## Implementation Checklist

- [x] Create `check_services.ps1` - service status checker
- [x] Create `start_vite.ps1` - simple starter
- [x] Create `start_vite_persistent.ps1` - persistent server with auto-restart
- [x] Create `scripts/README.md` - comprehensive documentation
- [x] Identify root cause (Vite not persistent)
- [ ] Choose reliability strategy:
  - [ ] Manual start (current, simple)
  - [ ] Scheduled task (recommended for dev)
  - [ ] Windows service (recommended for production)
  - [ ] Use containerized frontend (recommended for demos)

---

## Recommendations

**Immediate Action** (Today):
```powershell
# Start Vite with persistence for current session
.\scripts\start_vite_persistent.ps1
```

**Short-term** (This Week):
```powershell
# Set up auto-start on login (optional)
# See "Option B: Windows Scheduled Task" above
```

**Long-term** (Production):
```powershell
# Use containerized frontend for reliability
docker compose up -d frontend
# Access at http://localhost:3000
```

---

## Files Created

1. **`scripts/check_services.ps1`** - Service status checker
2. **`scripts/start_vite.ps1`** - Simple Vite starter
3. **`scripts/start_vite_persistent.ps1`** - Persistent Vite with auto-restart ⭐
4. **`scripts/README.md`** - Comprehensive script documentation
5. **`docs/VITE_RELIABILITY.md`** - This document

## Next Steps

1. **Test the persistent script**: `.\scripts\start_vite_persistent.ps1`
2. **Verify Vite is running**: `.\scripts\check_services.ps1`
3. **Access UI**: http://localhost:5173
4. **Choose long-term strategy**: Scheduled task, service, or containerized frontend
5. **Update documentation**: Add reliability section to USER_MANUAL.md (optional)
