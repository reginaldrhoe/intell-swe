from fastapi import HTTPException, Header
import os
import json
from typing import Dict, Any


def _load_token_roles() -> Dict[str, Any]:
    """Load token->role mapping from env `RAG_ROLE_TOKENS` (JSON) or `agents/rbac.json` file.

    Format example: {"token1": "admin", "token2": "viewer"}
    """
    env = os.getenv("RAG_ROLE_TOKENS")
    if env:
        try:
            return json.loads(env)
        except Exception:
            return {}
    # try file
    path = os.path.join(os.path.dirname(__file__), "..", "agents", "rbac.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def check_admin_token(authorization: str | None = Header(None), required_role: str | None = None) -> bool:
    """Check authorization header token and optionally require a role.

    - If no role mapping exists and no `RAG_ADMIN_TOKEN` is set, behave permissively for dev.
    - If `required_role` is provided, the token's role must match or be a superset (e.g., admin covers viewer).
    """
    roles = _load_token_roles()
    if not roles:
        # no role mapping — fall back to old single-token behavior
        token = os.getenv("RAG_ADMIN_TOKEN")
        if token is None:
            return True
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing Authorization header")
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1] == token:
            return True
        if authorization == token:
            return True
        raise HTTPException(status_code=403, detail="Invalid admin token")

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    token_val = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization
    role = roles.get(token_val)
    if role is None:
        raise HTTPException(status_code=403, detail="Invalid token or no role assigned")
    # simple role hierarchy
    hierarchy = {"viewer": 10, "editor": 20, "admin": 30}
    if required_role is None:
        return True
    if hierarchy.get(role, 0) >= hierarchy.get(required_role, 0):
        return True
    raise HTTPException(status_code=403, detail="Insufficient role for this action")
