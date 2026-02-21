# Database Configuration Guide

**Version**: 3.0  
**Last Updated**: 2026-01-27  
**Applies to**: rag-poc and intell-swe repositories

---

## Overview

The system supports **both MySQL and PostgreSQL** as the primary database. Choose based on your requirements:

| Database | Best For | Advantages | Disadvantages |
|----------|----------|------------|---------------|
| **MySQL 8.0** | Quick setup, development | Easy configuration, widely known | Less advanced features |
| **PostgreSQL 15** | Production, scale | Advanced features, better JSON support, JSONB | Slightly more complex |

**Default**: MySQL 8.0 (pre-configured in `docker-compose.yml`)

---

## Quick Switch: MySQL to PostgreSQL

### 1. Update .env File

**Comment out MySQL variables, uncomment PostgreSQL:**

```env
# OPTION A: MySQL 8.0 (Comment out if using PostgreSQL)
# DATABASE_URL=mysql+pymysql://raguser:strongpassword@mysql:3306/rag_poc
# MYSQL_ROOT_PASSWORD=changeme
# MYSQL_DATABASE=rag_poc
# MYSQL_USER=raguser
# MYSQL_PASSWORD=strongpassword

# OPTION B: PostgreSQL (Uncomment to use PostgreSQL)
DATABASE_URL=postgresql://postgres:strongpassword@postgres:5432/intell_swe
POSTGRES_USER=postgres
POSTGRES_PASSWORD=strongpassword
POSTGRES_DB=intell_swe
```

### 2. Update docker-compose.yml

**Comment out mysql service, uncomment postgres:**

```yaml
services:
  # ... other services ...

  # mysql:  # Comment out MySQL
  #   image: mysql:8.0
  #   # ... mysql config ...

  # PostgreSQL alternative (uncomment to use)
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-postgres}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-strongpassword}
      - POSTGRES_DB=${POSTGRES_DB:-intell_swe}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  qdrant_data:
  # mysql_data:  # Comment out
  postgres_data:  # Uncomment
```

### 3. Start PostgreSQL

```bash
# Stop existing services
docker compose down

# Start with PostgreSQL
docker compose up -d postgres redis qdrant mcp worker

# Verify PostgreSQL is running
docker compose ps postgres
docker compose logs postgres
```

### 4. Validate Configuration

```bash
python scripts/validate_env.py
```

---

## Database Connection Strings

### MySQL Format

```env
# Standard MySQL
DATABASE_URL=mysql+pymysql://user:password@host:port/database

# Examples
DATABASE_URL=mysql+pymysql://raguser:strongpassword@mysql:3306/rag_poc
DATABASE_URL=mysql+pymysql://root:changeme@localhost:3306/rag_poc
DATABASE_URL=mysql+pymysql://admin:pass@db.example.com:3306/production
```

### PostgreSQL Format

```env
# Standard PostgreSQL
DATABASE_URL=postgresql://user:password@host:port/database

# Alternative format (also works)
DATABASE_URL=postgres://user:password@host:port/database

# Examples
DATABASE_URL=postgresql://postgres:strongpassword@postgres:5432/intell_swe
DATABASE_URL=postgresql://admin:pass@localhost:5432/intell_swe
DATABASE_URL=postgresql://user:pass@db.example.com:5432/production
```

---

## Required Credentials by Database

### For MySQL

Required in `.env`:
```env
MYSQL_ROOT_PASSWORD=changeme          # Root password (for admin)
MYSQL_DATABASE=rag_poc                # Database name
MYSQL_USER=raguser                    # Application user
MYSQL_PASSWORD=strongpassword         # Application user password
```

### For PostgreSQL

Required in `.env`:
```env
POSTGRES_USER=postgres                # Superuser (default: postgres)
POSTGRES_PASSWORD=strongpassword      # Superuser password
POSTGRES_DB=intell_swe                # Database name
```

---

## Both Databases at Once (Advanced)

You can run both databases simultaneously for migration or testing:

### 1. Uncomment both services in docker-compose.yml

```yaml
services:
  mysql:
    image: mysql:8.0
    ports:
      - "3306:3306"  # MySQL port
    # ... config ...

  postgres:
    image: postgres:15
    ports:
      - "5432:5432"  # PostgreSQL port
    # ... config ...

volumes:
  mysql_data:
  postgres_data:
```

### 2. Configure both in .env

```env
# MySQL configuration
DATABASE_URL=mysql+pymysql://raguser:strongpassword@mysql:3306/rag_poc
MYSQL_ROOT_PASSWORD=changeme
MYSQL_DATABASE=rag_poc
MYSQL_USER=raguser
MYSQL_PASSWORD=strongpassword

# PostgreSQL configuration (for migration/testing)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=strongpassword
POSTGRES_DB=intell_swe
```

### 3. Start both

```bash
docker compose up -d mysql postgres redis qdrant
```

### 4. Switch between them by changing DATABASE_URL

```env
# Use MySQL
DATABASE_URL=mysql+pymysql://raguser:strongpassword@mysql:3306/rag_poc

# Or use PostgreSQL
DATABASE_URL=postgresql://postgres:strongpassword@postgres:5432/intell_swe
```

Restart services after changing `DATABASE_URL`.

---

## Migration: MySQL to PostgreSQL

### Option 1: Using pgloader (Recommended)

```bash
# Install pgloader
docker pull dimitri/pgloader

# Run migration
docker run --rm --network=host dimitri/pgloader \
  pgloader \
  mysql://raguser:strongpassword@localhost:3306/rag_poc \
  postgresql://postgres:strongpassword@localhost:5432/intell_swe
```

### Option 2: Dump and Restore

**Export from MySQL:**
```bash
docker compose exec mysql mysqldump -u raguser -pstrongpassword rag_poc > backup.sql
```

**Convert and Import to PostgreSQL:**
```bash
# Manual conversion required (MySQL SQL != PostgreSQL SQL)
# Use tools like: https://github.com/AnatolyUss/nmig
```

### Option 3: Application-Level Migration

Use SQLAlchemy's metadata reflection to copy data:

```python
from sqlalchemy import create_engine, MetaData

# Source
mysql_engine = create_engine("mysql+pymysql://raguser:strongpassword@mysql:3306/rag_poc")
# Target
pg_engine = create_engine("postgresql://postgres:strongpassword@postgres:5432/intell_swe")

# Reflect and copy
metadata = MetaData()
metadata.reflect(bind=mysql_engine)
metadata.create_all(pg_engine)
# ... copy data table by table ...
```

---

## Validation After Switch

After switching databases, validate your setup:

```bash
# 1. Validate .env configuration
python scripts/validate_env.py

# 2. Check database connectivity
docker compose exec mcp python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    print('✓ Database connection successful!')
"

# 3. Check application logs
docker compose logs mcp | grep -i database
docker compose logs mcp | grep -i error
```

---

## Troubleshooting

### MySQL Issues

**Connection refused:**
```bash
# Check MySQL is running
docker compose ps mysql
docker compose logs mysql

# Verify port
netstat -an | grep 3306
```

**Authentication error:**
- Check `MYSQL_USER` and `MYSQL_PASSWORD` match `.env`
- Ensure `DATABASE_URL` uses correct credentials

### PostgreSQL Issues

**Connection refused:**
```bash
# Check PostgreSQL is running
docker compose ps postgres
docker compose logs postgres

# Verify port
netstat -an | grep 5432
```

**Password authentication failed:**
- Check `POSTGRES_USER` and `POSTGRES_PASSWORD` in `.env`
- Ensure `DATABASE_URL` uses correct credentials
- PostgreSQL is case-sensitive for passwords

### General Database Issues

**"No module named 'pymysql'" or "No module named 'psycopg'":**
```bash
# Install database drivers
pip install pymysql psycopg[binary]
```

**SQLAlchemy dialect errors:**
- MySQL: Use `mysql+pymysql://` (NOT `mysql://`)
- PostgreSQL: Use `postgresql://` or `postgres://`

---

## Performance Tuning

### MySQL Optimization

Add to docker-compose.yml MySQL service:
```yaml
mysql:
  image: mysql:8.0
  command:
    - --max_connections=200
    - --innodb_buffer_pool_size=1G
    - --query_cache_size=0
```

### PostgreSQL Optimization

Add to docker-compose.yml PostgreSQL service:
```yaml
postgres:
  image: postgres:15
  command:
    - -c
    - max_connections=200
    - -c
    - shared_buffers=256MB
    - -c
    - effective_cache_size=1GB
```

---

## Security Best Practices

1. **Change default passwords**
   ```env
   # DON'T use these defaults in production!
   MYSQL_ROOT_PASSWORD=changeme          # ❌
   POSTGRES_PASSWORD=yourpassword        # ❌
   
   # Use strong passwords:
   MYSQL_ROOT_PASSWORD=Xy9#mK2$pQ8@vL5  # ✅
   POSTGRES_PASSWORD=Rz4&nB7!wT3%fH9    # ✅
   ```

2. **Use separate credentials for dev/staging/prod**

3. **Restrict network access**
   ```yaml
   mysql:
     ports:
       - "127.0.0.1:3306:3306"  # Only localhost
   ```

4. **Enable SSL/TLS for production**
   ```env
   DATABASE_URL=mysql+pymysql://user:pass@host:3306/db?ssl_ca=/path/to/ca.pem
   DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
   ```

---

## See Also

- [LLM Setup Guide](LLM_SETUP_GUIDE.md) - Configure OpenAI/Claude
- [Operation Manual](manuals/OPERATION_MANUAL.md) - Deployment guide
- [QUICKSTART_LLM.md](../QUICKSTART_LLM.md) - Quick reference
