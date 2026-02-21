#!/usr/bin/env python3
"""
.env File Validator

Validates that all required environment variables are present in .env file.
Run this before starting the application to catch configuration issues early.

Usage:
    python scripts/validate_env.py
    python scripts/validate_env.py --verbose
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def load_env_file(file_path: Path) -> Dict[str, str]:
    """Load .env file and return key-value pairs."""
    env_vars = {}
    if not file_path.exists():
        return env_vars
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value and not value.startswith('YOUR_') and not value.startswith('sk-proj-YOUR'):
                    env_vars[key] = value
    return env_vars


def check_requirements() -> Tuple[List[str], List[str], List[str]]:
    """Check required, optional, and missing environment variables."""
    
    # Required variables (at least one LLM key + infrastructure)
    required_vars = [
        'QDRANT_URL',
        'RAG_COLLECTION',
        'REDIS_URL',
        'CELERY_BROKER_URL',
        'DATABASE_URL',
    ]
    
    # Database credentials (MySQL or PostgreSQL - depends on DATABASE_URL)
    database_vars = {
        'mysql': ['MYSQL_DATABASE', 'MYSQL_USER', 'MYSQL_PASSWORD'],
        'postgres': ['POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
    }
    
    # LLM keys (at least one required)
    llm_keys = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    
    # Optional but recommended
    optional_vars = [
        'CREWAI_MODEL',
        'CREWAI_PROVIDER',
        'OPENAI_DEFAULT_TEMPERATURE',
        'MYSQL_ROOT_PASSWORD',
        'POSTGRES_PASSWORD',
    ]
    
    # Load .env file
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    
    if not env_file.exists():
        print(f"{RED}✗ ERROR: .env file not found at {env_file}{RESET}\n")
        print(f"Please create .env from template:")
        print(f"  {BLUE}cp .env.example .env{RESET}")
        print(f"  {BLUE}# Then edit .env with your actual values{RESET}\n")
        sys.exit(1)
    
    env_vars = load_env_file(env_file)
    
    # Detect database type from DATABASE_URL
    db_type = 'mysql'  # default
    if 'DATABASE_URL' in env_vars:
        if 'postgresql://' in env_vars['DATABASE_URL'] or 'postgres://' in env_vars['DATABASE_URL']:
            db_type = 'postgres'
        elif 'mysql' in env_vars['DATABASE_URL']:
            db_type = 'mysql'
    
    # Add database-specific required vars
    required_vars.extend(database_vars.get(db_type, []))
    
    # Check required variables
    missing = []
    present = []
    for var in required_vars:
        if var in env_vars:
            present.append(var)
        else:
            missing.append(var)
    
    # Check LLM keys (at least one)
    llm_present = [key for key in llm_keys if key in env_vars]
    
    # Check optional variables
    optional_present = [var for var in optional_vars if var in env_vars]
    optional_missing = [var for var in optional_vars if var not in env_vars]
    
    return present, missing, optional_present, optional_missing, llm_present


def validate_values(env_vars: Dict[str, str]) -> List[str]:
    """Validate that values are not placeholder defaults."""
    warnings = []
    
    # Check for placeholder values
    for key, value in env_vars.items():
        if 'YOUR_' in value.upper() or 'CHANGEME' in value.upper():
            warnings.append(f"{key} contains placeholder value: '{value}'")
        if key == 'MYSQL_ROOT_PASSWORD' and value == 'changeme':
            warnings.append(f"{key} is using default insecure password")
        if key == 'MYSQL_PASSWORD' and value == 'strongpassword':
            warnings.append(f"{key} is using default password (consider changing for production)")
    
    return warnings


def main():
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}  Environment Configuration Validator{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")
    
    present, missing, optional_present, optional_missing, llm_present = check_requirements()
    
    # Load env for value validation
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    env_vars = load_env_file(env_file)
    
    # Check LLM keys
    print(f"{BOLD}LLM API Keys:{RESET}")
    if llm_present:
        for key in llm_present:
            print(f"  {GREEN}✓{RESET} {key} is set")
    else:
        print(f"  {RED}✗{RESET} No LLM API key found (need OPENAI_API_KEY or ANTHROPIC_API_KEY)")
        missing.append("OPENAI_API_KEY or ANTHROPIC_API_KEY")
    print()
    
    # Check required variables
    print(f"{BOLD}Required Variables:{RESET}")
    if verbose or missing:
        for var in present:
            print(f"  {GREEN}✓{RESET} {var}")
        for var in missing:
            print(f"  {RED}✗{RESET} {var} {RED}(MISSING){RESET}")
    else:
        print(f"  {GREEN}✓{RESET} All {len(present)} required variables present")
    print()
    
    # Check optional variables
    if verbose:
        print(f"{BOLD}Optional Variables:{RESET}")
        for var in optional_present:
            print(f"  {GREEN}✓{RESET} {var}")
        for var in optional_missing:
            print(f"  {YELLOW}○{RESET} {var} (not set, using defaults)")
        print()
    
    # Validate values
    warnings = validate_values(env_vars)
    if warnings:
        print(f"{BOLD}{YELLOW}Warnings:{RESET}")
        for warning in warnings:
            print(f"  {YELLOW}⚠{RESET}  {warning}")
        print()
    
    # Summary
    print(f"{BOLD}{'='*70}{RESET}")
    if missing or not llm_present:
        print(f"{RED}✗ VALIDATION FAILED{RESET}")
        print(f"\n{BOLD}Missing required variables:{RESET}")
        for var in (missing if missing else ["OPENAI_API_KEY or ANTHROPIC_API_KEY"]):
            print(f"  • {var}")
        print(f"\n{BOLD}To fix:{RESET}")
        print(f"  1. Open .env file: {BLUE}{env_file}{RESET}")
        print(f"  2. Add missing variables (see .env.example for reference)")
        print(f"  3. Run this validator again\n")
        sys.exit(1)
    else:
        print(f"{GREEN}✓ VALIDATION PASSED{RESET}")
        if warnings:
            print(f"{YELLOW}  Note: {len(warnings)} warning(s) - review before production deployment{RESET}")
        print()
        sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Validation cancelled{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        sys.exit(1)
