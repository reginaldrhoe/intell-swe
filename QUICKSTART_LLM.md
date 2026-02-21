# Quick Reference: LLM Setup (1-Page Cheat Sheet)

**Version**: 3.0 | **Date**: 2026-01-27

---

## Where to Create `.env` File

The `.env` file **must be in the root directory** of the repository:

**Location**: `C:\MySQL\intell_swe\.env` (Windows) or `~/intell-swe/.env` (Mac/Linux)

### How to Create It

**Option 1: Windows PowerShell**
```powershell
cd C:\MySQL\intell_swe
echo "OPENAI_API_KEY=sk-proj-YOUR_KEY" > .env
```

**Option 2: Mac/Linux Terminal**
```bash
cd ~/intell-swe
echo "OPENAI_API_KEY=sk-proj-YOUR_KEY" > .env
```

**Option 3: VS Code**
1. File → Open Folder → `intell_swe`
2. File → New File → name it `.env`
3. Save in root folder (next to README.md)

### How to Find It

- **Windows File Explorer**: Press `Ctrl+H` to show hidden files
- **VS Code**: Open root folder; look in File Explorer sidebar
- **Terminal**: Run `Get-Item .env -Force` or `ls -la | grep .env`

The file may be hidden because it starts with a dot (`.`).

---

## 5-Minute Setup

### Option A: Use OpenAI (gpt-4o-mini)
```bash
# 1. Get key from https://platform.openai.com/account/api-keys
# 2. Create .env
cat > .env << EOF
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
CREWAI_MODEL=gpt-4o-mini
QDRANT_URL=http://qdrant:6333
REDIS_URL=redis://redis:6379/0
EOF

# 3. Start services
docker compose up -d redis qdrant mcp worker mysql

# 4. Done! Access at http://localhost:5173
```

### Option B: Use Claude (cheaper!)
```bash
# 1. Get key from https://console.anthropic.com/settings/keys
# 2. Create .env
cat > .env << EOF
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
CREWAI_MODEL=claude-3-5-haiku-20241022
QDRANT_URL=http://qdrant:6333
REDIS_URL=redis://redis:6379/0
EOF

# 3. Start services
docker compose up -d redis qdrant mcp worker mysql

# 4. Done! Access at http://localhost:5173
```

---

## Models at a Glance

| Provider | Model | Speed | Cost | Use Case |
|----------|-------|-------|------|----------|
| **OpenAI** | gpt-4o | Slow | $$ | High accuracy |
| **OpenAI** | gpt-4o-mini | Fast | $ | Development |
| **Claude** | claude-3-5-sonnet | Medium | $ | Balanced |
| **Claude** | claude-3-5-haiku | Fast | ¢ | Quick tasks |

---

## Validation

After creating `.env`, verify configuration:

```bash
# Check if .env exists
ls -la .env  # Mac/Linux
Get-Item .env -Force  # PowerShell

# Check keys are set
cat .env  # Mac/Linux
Get-Content .env  # PowerShell

# Test Docker startup
docker compose up -d
docker compose logs -f
```

---

## Troubleshooting

**Issue**: `.env` file not found
- Solution: Create it in root folder (next to README.md)
- Check: Press `Ctrl+H` (Windows) or `Cmd+Shift+.` (Mac) to show hidden files

**Issue**: Keys not loading
- Solution: Make sure `.env` is in exact location
- Check: No spaces in paths, file is named `.env` (not `.env.txt`)

**Issue**: API key errors
- Solution: Verify key from platform.openai.com or console.anthropic.com
- Check: Key starts with `sk-proj-` (OpenAI) or `sk-ant-` (Claude)

See [docs/LLM_SETUP_GUIDE.md](docs/LLM_SETUP_GUIDE.md) for complete documentation.
