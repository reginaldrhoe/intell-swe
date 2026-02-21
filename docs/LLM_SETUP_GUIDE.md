# LLM Setup & Configuration Guide

**Version**: 3.0  
**Last Updated**: 2026-01-27  
**Applies to**: rag-poc and intell-swe repositories

## Table of Contents

1. [Environment File (.env) Setup](#environment-file-env-setup)
2. [Overview](#overview)
3. [OpenAI Setup](#openai-setup)
4. [Claude/Anthropic Setup](#claudeanthropicsetup)
5. [Provider Auto-Detection](#provider-auto-detection)
6. [Deployment Configuration](#deployment-configuration)
7. [Troubleshooting](#troubleshooting)

---

## Environment File (.env) Setup

### Where to Place the .env File

The `.env` file **must be located in the root directory** of your repository. This is the same directory where you see:
- `README.md`
- `requirements.txt`
- `docker-compose.yml`
- `agents/` folder
- `docs/` folder

**Full Path Examples**:
- **Windows**: `C:\MySQL\intell_swe\.env`
- **Mac/Linux**: `/home/user/intell-swe/.env` or `~/intell-swe/.env`

### How to Create .env File

#### Method 1: Terminal/Command Line (Recommended)

**Windows PowerShell**:
```powershell
cd C:\MySQL\intell_swe
# Create empty .env file
New-Item -Path ".env" -ItemType File

# Or create with initial content
echo "OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE" > .env
```

**Mac/Linux Terminal**:
```bash
cd ~/intell-swe
touch .env
# Or create with initial content
echo "OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE" > .env
```

#### Method 2: Visual Studio Code (Easy)

1. Open VS Code
2. File → Open Folder → select `intell_swe`
3. File → New File
4. Name it `.env` (exactly, with the dot)
5. Save it in the root folder (next to README.md)
6. Add your API key configuration (see examples below)

#### Method 3: Text Editor (Manual)

1. Open **Notepad** (Windows), **TextEdit** (Mac), or any text editor
2. Type your configuration:
   ```env
   OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
   CREWAI_MODEL=gpt-4o-mini
   ```
3. Save as → Filename: `.env` (with the dot)
4. Save Location: Root of your `intell_swe` folder
5. File Type: "All Files" (not .txt)

### How to Find Existing .env File

#### In VS Code:
1. Open the repository folder in VS Code
2. Look in the **File Explorer** (left sidebar) for `.env`
3. If you don't see it:
   - It may be hidden; check Settings → Files: Exclude
   - Or it simply doesn't exist yet (create one using Method 2 above)

#### In Windows File Explorer:
1. Navigate to `C:\MySQL\intell_swe\`
2. If `.env` isn't visible:
   - View → Show hidden files (or press `Ctrl+H`)
   - Look for `.env` in the file list
3. Once visible, right-click → Open with → Notepad or VS Code

#### In Mac Finder:
1. Navigate to your project folder
2. Press `Cmd+Shift+.` to toggle hidden files visibility
3. Look for `.env` file
4. Double-click to open with default editor

#### In Terminal:
```bash
# Windows PowerShell
cd C:\MySQL\intell_swe
Get-Item .env -Force  # Shows the file if it exists
cat .env  # Shows contents

# Mac/Linux
cd ~/intell-swe
ls -la | grep .env  # Shows the file if it exists
cat .env  # Shows contents
```

### .env File Is Ignored by Git (Security)

The `.env` file is **intentionally NOT committed to git** for security:
- It contains your API keys (secrets)
- Each developer/deployment needs their own `.env`
- It's listed in `.gitignore` to prevent accidental commits

**This means**:
- ✅ You MUST create `.env` manually in each environment
- ✅ Everyone gets their own `.env` with their own API keys
- ✅ Keys stay secret and never push to GitHub
- ✅ Example template: see `.env.example` (if provided) or follow this guide

---

## Overview

The system supports **two LLM providers** for intelligent agent analysis:

- **OpenAI** (recommended for production)
  - Most widely used, excellent documentation
  - Models: gpt-4o (best), gpt-4-turbo, gpt-4o-mini (cheapest)
  
- **Claude/Anthropic** (alternative, excellent for code)
  - Longer context window, better for code analysis
  - Models: claude-3-5-sonnet (balanced), haiku (fast), opus (most capable)

The system **automatically detects** which provider to use based on available API keys.

---

## OpenAI Setup

### Step 1: Create OpenAI Account

1. Go to [platform.openai.com](https://platform.openai.com)
2. Click "Sign up"
3. Create account with email or GitHub/Microsoft sign-in
4. Verify email address
5. Accept terms of service

### Step 2: Create API Key

1. Navigate to [API Keys page](https://platform.openai.com/account/api-keys)
2. Click **"Create new secret key"**
3. **Copy the key immediately** (you won't see it again!)
4. Give it a descriptive name like:
   - `rag-poc-production`
   - `rag-poc-development`
   - `intell-swe-staging`

### Step 3: Set Up Billing

1. Go to [Billing settings](https://platform.openai.com/account/billing/overview)
2. Click **"Add payment method"**
3. Enter credit card details
4. (Recommended) Set **usage limits** under "Usage limits" to avoid unexpected charges

### Step 4: Configure Environment

Add to your `.env` file:

```env
# Required
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE

# Optional (defaults shown)
CREWAI_MODEL=gpt-4o-mini
OPENAI_DEFAULT_TEMPERATURE=0.2
```

### Model Selection Guide

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| **gpt-4o** | Slow | Medium | Complex analysis, maximum accuracy |
| **gpt-4-turbo** | Medium | Medium | Balanced cost/capability |
| **gpt-4o-mini** | Fast | Low | Quick tasks, simple analysis, testing |

**Recommendation**: Start with `gpt-4o-mini` for development/testing, upgrade to `gpt-4o` for production if needed.

### Cost Estimation

**Typical Agent Run**:
- Input tokens: ~3,000-5,000 (code context)
- Output tokens: ~1,000-2,000 (analysis)
- Total: ~4,000-7,000 tokens per run

**Cost per run**:
- gpt-4o-mini: ~$0.02-0.05
- gpt-4-turbo: ~$0.03-0.07
- gpt-4o: ~$0.05-0.15

**Monthly estimate** (100 runs):
- gpt-4o-mini: $2-5
- gpt-4-turbo: $3-7
- gpt-4o: $5-15

---

## Claude/Anthropic Setup

### Step 1: Create Anthropic Account

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Click "Sign up"
3. Create account with email
4. Verify email address
5. Accept terms

### Step 2: Create API Key

1. Navigate to **Settings → API Keys**
2. Click **"Create Key"**
3. **Copy the key immediately**
4. Give it a descriptive name

### Step 3: Set Up Billing

1. Go to **Settings → Plans & Billing**
2. Click **"Add payment method"**
3. Enter credit card details
4. (Optional) Set spending quota

### Step 4: Configure Environment

Add to your `.env` file:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE

# Optional
CREWAI_MODEL=claude-3-5-sonnet-20241022
CREWAI_PROVIDER=anthropic  # Optional: force use of Anthropic
```

### Model Selection Guide

| Model | Speed | Cost | Context | Best For |
|-------|-------|------|---------|----------|
| **claude-3-5-haiku-20241022** | Fastest | Lowest (~$0.0008) | 200K | Quick tasks, large docs |
| **claude-3-5-sonnet-20241022** | Medium | Medium (~$0.003) | 200K | **Recommended**: code analysis |
| **claude-3-opus-20250219** | Slow | Highest (~$0.015) | 200K | Complex reasoning |

**Recommendation**: Use `claude-3-5-sonnet-20241022` for best balance of speed, cost, and capability.

### Cost Estimation

**Typical Agent Run**:
- Input: ~3,000-5,000 tokens
- Output: ~1,000-2,000 tokens
- Total: ~4,000-7,000 tokens

**Cost per run**:
- Haiku: ~$0.005-0.01 (cheapest!)
- Sonnet: ~$0.015-0.03
- Opus: ~$0.05-0.10

**Monthly estimate** (100 runs):
- Haiku: $0.50-1.00 (best value!)
- Sonnet: $1.50-3.00
- Opus: $5-10

---

## Provider Auto-Detection

The system intelligently selects which provider to use:

### Detection Priority

```
1. Explicit CREWAI_PROVIDER environment variable
   ├─ CREWAI_PROVIDER=openai  → use OpenAI
   └─ CREWAI_PROVIDER=anthropic  → use Claude

2. Available API keys
   ├─ If ANTHROPIC_API_KEY exists → use Claude
   ├─ Else if OPENAI_API_KEY exists → use OpenAI
   └─ Else → use stub mode (offline)

3. Fallback: Stub mode (no real API calls, for testing)
```

### Verify Auto-Detection

Run this command to see which provider will be used:

```powershell
python -c "
from agents.core.crewai_adapter import CrewAIAdapter
adapter = CrewAIAdapter()
print(f'Provider: {adapter.provider}')
print(f'Model: {adapter.model}')
"
```

Expected output:
```
Provider: openai
Model: gpt-4o-mini
```

or

```
Provider: anthropic
Model: claude-3-5-sonnet-20241022
```

### Example Scenarios

**Scenario 1: Use OpenAI (explicit)**
```env
OPENAI_API_KEY=sk-proj-...
CREWAI_MODEL=gpt-4o-mini
# CREWAI_PROVIDER not set → auto-detects OpenAI
```

**Scenario 2: Use Claude (explicit)**
```env
ANTHROPIC_API_KEY=sk-ant-...
CREWAI_MODEL=claude-3-5-sonnet-20241022
# CREWAI_PROVIDER=anthropic  ← explicitly force if needed
```

**Scenario 3: Both keys present (Claude wins)**
```env
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
# System uses Claude (Anthropic has priority)
# To override, set: CREWAI_PROVIDER=openai
```

**Scenario 4: Test without API keys (stub mode)**
```env
# No OPENAI_API_KEY or ANTHROPIC_API_KEY
# System uses stub mode (no real API calls)
# Useful for testing CI/CD pipelines
```

---

## Deployment Configuration

### Docker Compose

```yaml
services:
  mcp:
    image: your-registry/rag-poc-mcp:latest
    environment:
      # LLM Configuration (choose one)
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      # OR
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      
      CREWAI_MODEL: ${CREWAI_MODEL:-gpt-4o-mini}
      CREWAI_PROVIDER: ${CREWAI_PROVIDER:-}  # empty for auto-detect
      
      # System Configuration
      QDRANT_URL: http://qdrant:6333
      REDIS_URL: redis://redis:6379/0
      DATABASE_URL: mysql+pymysql://user:pass@mysql:3306/db
    
    # Security: use external env file, not hardcoded
    env_file:
      - production.env
```

**Deploy**:
```bash
docker compose --env-file production.env up -d
```

### Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-poc-llm-keys
type: Opaque
stringData:
  OPENAI_API_KEY: sk-proj-...      # OR use Anthropic key
  # ANTHROPIC_API_KEY: sk-ant-...
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-poc-mcp
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: mcp
        image: your-registry/rag-poc-mcp:latest
        envFrom:
        - secretRef:
            name: rag-poc-llm-keys
        env:
        - name: CREWAI_MODEL
          value: "gpt-4o-mini"
        - name: CREWAI_PROVIDER
          value: ""  # auto-detect
```

**Deploy**:
```bash
kubectl apply -f deployment.yaml
kubectl rollout status deployment/rag-poc-mcp
```

---

## Troubleshooting

### Issue: "401 Unauthorized" or "Invalid API Key"

**Solution**:
1. Verify API key is correct (copy from OpenAI/Anthropic dashboard)
2. Check `.env` file for typos
3. Ensure key has permissions (check in dashboard)
4. For OpenAI: verify billing is set up

```bash
# Test OpenAI key
python -c "
from openai import OpenAI
import os
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
models = client.models.list()
print(f'✓ OpenAI key valid, found {len(models.data)} models')
"

# Test Anthropic key
python -c "
from anthropic import Anthropic
import os
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
msg = client.messages.create(
    model='claude-3-5-haiku-20241022',
    max_tokens=10,
    messages=[{'role': 'user', 'content': 'Hi'}]
)
print('✓ Anthropic key valid')
"
```

### Issue: "Model not found" or "Invalid model name"

**Solution**:
1. Verify model name is correct for the provider
2. Check OpenAI/Anthropic documentation for available models

**Valid OpenAI models**:
- `gpt-4o`
- `gpt-4-turbo`
- `gpt-4o-mini`

**Valid Anthropic models**:
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`
- `claude-3-opus-20250219`

### Issue: "Adapter used wrong provider"

**Solution**:
1. Verify which provider is being used:

```bash
python -c "from agents.core.crewai_adapter import CrewAIAdapter; a = CrewAIAdapter(); print(f'{a.provider}: {a.model}')"
```

2. If wrong provider detected:
   - Check which API keys are set: `echo $OPENAI_API_KEY $ANTHROPIC_API_KEY`
   - Set explicit provider: `export CREWAI_PROVIDER=anthropic`

### Issue: "Rate limit exceeded"

**Solution**:
1. Reduce number of concurrent tasks
2. Add backoff/retry logic (already in adapter)
3. Upgrade API plan with provider
4. Use cheaper model (gpt-4o-mini or haiku)

---

## Security Best Practices

### ✅ DO:
- Store API keys in `.env` (which is `.gitignored`)
- Use environment variables in production
- Use Docker secrets or Kubernetes secrets
- Rotate keys regularly
- Set usage limits in provider dashboards

### ❌ DON'T:
- Commit `.env` to git
- Hardcode API keys in source code
- Share API keys in chat/Slack
- Use personal keys in shared environments
- Store keys in Docker images

**Example secure deployment**:
```bash
# Create external env file (NOT in git)
cat > production.env << EOF
OPENAI_API_KEY=sk-proj-YOUR_KEY
CREWAI_MODEL=gpt-4o-mini
EOF

# Deploy with secrets
docker compose --env-file production.env up -d

# Cleanup
rm production.env  # Delete local copy
```

---

## Quick Reference

### OpenAI
- Get key: https://platform.openai.com/account/api-keys
- Pricing: https://openai.com/pricing
- Models: gpt-4o, gpt-4-turbo, gpt-4o-mini
- Env var: `OPENAI_API_KEY`

### Claude/Anthropic
- Get key: https://console.anthropic.com/settings/keys
- Pricing: https://www.anthropic.com/pricing
- Models: claude-3-5-sonnet-20241022, haiku, opus
- Env var: `ANTHROPIC_API_KEY`

### Configuration
- Model selection: `CREWAI_MODEL`
- Provider override: `CREWAI_PROVIDER=openai|anthropic`
- Temperature: `OPENAI_DEFAULT_TEMPERATURE=0.2`

### CrewAI Agent Framework
- **Purpose**: Multi-agent orchestration and task delegation for intelligent code analysis
- **Installation**: `pip install crewai>=0.1.0` (optional; auto-detects OpenAI or Anthropic)
- **Environment variables**:
  - `CREWAI_MODEL` - Agent model (auto-detects from OpenAI or Anthropic)
  - `CREWAI_PROVIDER` - Force provider (openai, anthropic, or empty for auto-detect)
  - `CREWAI_API_KEY` - CrewAI cloud credentials (optional)
- **Fallback**: If CrewAI not installed, falls back to direct OpenAI/Anthropic API calls
- **Agent types**: Code review, root cause analysis, defect discovery, requirements tracing, performance metrics, audit
- **See**: [docs/manuals/AGENT_ENHANCEMENTS.md](../manuals/AGENT_ENHANCEMENTS.md) for detailed agent configuration

---

For architecture details, see [docs/architecture/ARCHITECTURE_ANALYSIS.md](../architecture/ARCHITECTURE_ANALYSIS.md)  
For deployment, see [docs/manuals/OPERATION_MANUAL.md](../manuals/OPERATION_MANUAL.md)
