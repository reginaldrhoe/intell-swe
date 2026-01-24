
import sys
import os

# Add root to path
sys.path.append(os.getcwd())

print("Verifying imports...")

try:
    print("Importing agents.core.agents...")
    import agents.core.agents
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

try:
    print("Importing agents.services.celery_queue...")
    import agents.services.celery_queue
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

try:
    print("Importing agents.impl.engineer_crewai...")
    import agents.impl.engineer_crewai
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

try:
    print("Importing mcp.mcp...")
    import mcp.mcp
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

print("Done.")
