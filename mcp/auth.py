from fastapi import HTTPException, Header
import os


def check_admin_token(authorization: str | None = Header(None)) -> bool:
    """Simple RBAC-like check for admin endpoints.

    - If `RAG_ADMIN_TOKEN` is not set, allow access (dev mode).
    - If set, require the Authorization Bearer token to match.
    - Can be extended to support roles (RAG_ADMIN_ROLE) later.
    """
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
