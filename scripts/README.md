# Development Scripts

Utility scripts for managing the RAG-POC development environment.

## Quick Start

```powershell
# Check service status
.\scripts\check_services.ps1

# Start Vite dev UI (simple, exits on error)
.\scripts\start_vite.ps1

# Start Vite with auto-restart (persistent)
.\scripts\start_vite_persistent.ps1

# Start Vite with custom API base
.\scripts\start_vite.ps1 -ApiBase "http://192.168.1.100:8001"
```

## Scripts

### `check_services.ps1`
Check status of all development services (Vite, API, MySQL, Redis, Qdrant, Frontend).

**Usage:**
```powershell
.\scripts\check_services.ps1
```

**Output:**
- ✅/❌ status for each service
- Port numbers and URLs
- Docker container status
- Quick action commands

---

### `start_vite.ps1`
Simple Vite dev server starter. Exits immediately if server crashes.

**Usage:**
```powershell
# Default (API at localhost:8001)
.\scripts\start_vite.ps1

# Custom API base
.\scripts\start_vite.ps1 -ApiBase "http://api.example.com:8001"
```

**Features:**
- Auto-installs dependencies if missing
- Sets `VITE_API_URL` environment variable
- Single-shot execution (no auto-restart)

**When to use:** Testing, one-time runs, debugging

---

### `start_vite_persistent.ps1`
Persistent Vite server with auto-restart on crashes.

**Usage:**
```powershell
# Unlimited restarts (default)
.\scripts\start_vite_persistent.ps1

# Limit restarts
.\scripts\start_vite_persistent.ps1 -MaxRestarts 5

# Disable auto-restart (like start_vite.ps1)
.\scripts\start_vite_persistent.ps1 -NoAutoRestart

# Custom API + restart limit
.\scripts\start_vite_persistent.ps1 -ApiBase "http://192.168.1.100:8001" -MaxRestarts 10
```

**Features:**
- Automatic restart on crashes (not on clean exit/Ctrl+C)
- Restart counter and timestamps
- Configurable restart limits
- 3-second delay between restarts

**When to use:** Development sessions, CI/CD, production-like testing

---

### `start_dev_ui.ps1` *(Legacy)*
Original persistent dev server script. Use `start_vite_persistent.ps1` instead.

**Differences:**
- Uses `cmd /c` wrapper (slower)
- No restart limit
- Less informative output

**Migration:**
```powershell
# Old
.\scripts\start_dev_ui.ps1

# New (equivalent)
.\scripts\start_vite_persistent.ps1
```

---

### `md_to_pdf.py`
Convert Markdown documentation to PDF format.

**Usage:**
```powershell
python scripts/md_to_pdf.py docs/USER_MANUAL.md docs/USER_MANUAL.pdf
```

**Requirements:**
```powershell
pip install reportlab
```

---

## Common Tasks

### Starting a Full Development Environment

```powershell
# 1. Check current status
.\scripts\check_services.ps1

# 2. Start Docker services
docker compose up -d

# 3. Wait for services to be ready (30 seconds)
Start-Sleep -Seconds 30

# 4. Start Vite dev UI (in separate terminal)
.\scripts\start_vite_persistent.ps1
```

### Troubleshooting Port Conflicts

```powershell
# Check what's using port 5173
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 5173 }

# Kill process by ID (if needed)
Stop-Process -Id <PID> -Force
```

### Automated Startup (Windows Task Scheduler)

Create a scheduled task to auto-start Vite on login:

```powershell
$action = New-ScheduledTaskAction -Execute "pwsh.exe" `
    -Argument "-File C:\MySQL\agentic_rag_poc\scripts\start_vite_persistent.ps1"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "RAG-POC Vite Dev" -Action $action -Trigger $trigger -Principal $principal
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8001` | Backend API base URL |
| `VITE_DEV_HOST` | unset | Set to "1" to expose dev server on network |

**Example:**
```powershell
$env:VITE_API_URL = "http://192.168.1.100:8001"
npm run dev
```

---

## Service Port Reference

| Service | Port | URL |
|---------|------|-----|
| Vite Dev UI | 5173 | http://localhost:5173 |
| API (MCP) | 8001 | http://localhost:8001 |
| Frontend (nginx) | 3000 | http://localhost:3000 |
| MySQL | 3306 | localhost:3306 |
| Redis | 6379 | localhost:6379 |
| Qdrant | 6333 | http://localhost:6333 |
| Prometheus | 9090 | http://localhost:9090 |

---

## Reliability Best Practices

### Development Workflow
1. **Always check status first:** `.\scripts\check_services.ps1`
2. **Use persistent script for long sessions:** `start_vite_persistent.ps1`
3. **Monitor logs:** Keep terminal visible to catch errors early
4. **Graceful shutdown:** Use Ctrl+C (not closing terminal window)

### CI/CD Integration
```yaml
# .gitlab-ci.yml or GitHub Actions
- name: Start dev services
  run: |
    pwsh -File scripts/start_vite_persistent.ps1 -MaxRestarts 3 &
    sleep 10
    curl http://localhost:5173
```

### Production-like Testing
```powershell
# Use containerized frontend instead of Vite
docker compose up -d frontend
# Access at http://localhost:3000
```

---

## Troubleshooting

### Vite won't start
```powershell
# 1. Check dependencies
cd web
npm install

# 2. Clear Vite cache
rm -Recurse -Force .vite

# 3. Check for port conflicts
.\scripts\check_services.ps1

# 4. Check logs
npm run dev  # Run once to see error
```

### Auto-restart loop (crash on startup)
```powershell
# Run without auto-restart to see error
.\scripts\start_vite.ps1

# Common causes:
# - Missing .env file
# - Port 5173 already in use
# - Syntax error in vite.config.js
```

### API connection refused
```powershell
# Verify API is running
curl http://localhost:8001/health

# If not running, start Docker services
docker compose up -d mcp
```

---

## See Also

- [USER_MANUAL.md](../docs/USER_MANUAL.md) - End-user documentation
- [OPERATION_MANUAL.md](../docs/OPERATION_MANUAL.md) - Operational procedures
- [docker-compose.yml](../docker-compose.yml) - Container orchestration
