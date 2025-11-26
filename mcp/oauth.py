import os
import secrets
import time
from typing import Optional

import requests
import jwt
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from .db import SessionLocal
from .models import User

router = APIRouter()

# Environment variables (configure these in your environment)
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITLAB_CLIENT_ID = os.getenv("GITLAB_CLIENT_ID")
GITLAB_CLIENT_SECRET = os.getenv("GITLAB_CLIENT_SECRET")
OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:8000")
JWT_SECRET = os.getenv("OAUTH_JWT_SECRET", "dev-secret")
JWT_ALGO = "HS256"
JWT_EXP_SECONDS = int(os.getenv("OAUTH_JWT_EXP_SECONDS", "3600"))

# In-memory state store for CSRF protection (MVP only; use persistent store in prod)
_state_store = {}


def _create_jwt(payload: dict) -> str:
    now = int(time.time())
    data = {"iat": now, "exp": now + JWT_EXP_SECONDS, **payload}
    token = jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGO)
    # PyJWT may return bytes in some versions
    if isinstance(token, bytes):
        token = token.decode()
    return token


@router.get("/auth/login")
def auth_login(provider: str = Query("github")):
    """Start OAuth flow for `provider` ('github' or 'gitlab').

    Redirects the user to the provider's authorization URL. For MVP we keep a
    short-lived state token in memory.
    """
    state = secrets.token_urlsafe(16)
    _state_store[state] = int(time.time())

    if provider == "github":
        if not GITHUB_CLIENT_ID:
            raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID not configured")
        redirect_uri = f"{OAUTH_REDIRECT_BASE}/auth/callback?provider=github"
        params = {
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
            "allow_signup": "true",
        }
        url = "https://github.com/login/oauth/authorize"
        return RedirectResponse(url + "?" + requests.compat.urlencode(params))

    elif provider == "gitlab":
        if not GITLAB_CLIENT_ID:
            raise HTTPException(status_code=500, detail="GITLAB_CLIENT_ID not configured")
        redirect_uri = f"{OAUTH_REDIRECT_BASE}/auth/callback?provider=gitlab"
        params = {
            "client_id": GITLAB_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "read_user",
            "state": state,
        }
        url = "https://gitlab.com/oauth/authorize"
        return RedirectResponse(url + "?" + requests.compat.urlencode(params))

    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")


@router.get("/auth/callback")
def auth_callback(request: Request, provider: str = Query("github"), code: Optional[str] = Query(None), state: Optional[str] = Query(None)):
    """Callback endpoint the OAuth provider redirects to.

    Exchanges `code` for an access token, fetches the user's identity, creates
    or finds a local `User` record, and returns a JWT for authenticating API calls.
    """
    if not state or state not in _state_store:
        raise HTTPException(status_code=400, detail="Missing or invalid state")

    # simple TTL for state values (120s)
    ts = _state_store.get(state)
    if not ts or (int(time.time()) - ts) > 120:
        _state_store.pop(state, None)
        raise HTTPException(status_code=400, detail="Expired state")

    _state_store.pop(state, None)

    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    if provider == "github":
        if not (GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET):
            raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
        token_url = "https://github.com/login/oauth/access_token"
        headers = {"Accept": "application/json"}
        data = {
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": f"{OAUTH_REDIRECT_BASE}/auth/callback?provider=github",
            "state": state,
        }
        resp = requests.post(token_url, data=data, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Token exchange failed")
        j = resp.json()
        access_token = j.get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="No access token returned")
        # fetch user
        uresp = requests.get("https://api.github.com/user", headers={"Authorization": f"token {access_token}"}, timeout=10)
        if uresp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch user info")
        user_json = uresp.json()
        username = user_json.get("login")
        email = user_json.get("email")

    elif provider == "gitlab":
        if not (GITLAB_CLIENT_ID and GITLAB_CLIENT_SECRET):
            raise HTTPException(status_code=500, detail="GitLab OAuth not configured")
        token_url = "https://gitlab.com/oauth/token"
        data = {
            "client_id": GITLAB_CLIENT_ID,
            "client_secret": GITLAB_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{OAUTH_REDIRECT_BASE}/auth/callback?provider=gitlab",
        }
        resp = requests.post(token_url, data=data, timeout=10)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Token exchange failed")
        j = resp.json()
        access_token = j.get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="No access token returned")
        uresp = requests.get("https://gitlab.com/api/v4/user", headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        if uresp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch user info")
        user_json = uresp.json()
        username = user_json.get("username")
        email = user_json.get("email")

    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    if not username:
        raise HTTPException(status_code=502, detail="Provider did not return username")

    # create or find user in DB
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username, email=email, role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
    finally:
        db.close()

    # Create JWT token with minimal claims
    token = _create_jwt({"sub": username, "uid": user.id, "role": user.role})

    # For a simple web flow, redirect back to a frontend URL with token as fragment
    frontend_callback = os.getenv("OAUTH_FRONTEND_CALLBACK", "http://localhost:3000/" )
    # Return token in fragment so SPA can read it (avoid logs in URL query)
    redirect_url = f"{frontend_callback}#access_token={token}&provider={provider}"
    return RedirectResponse(redirect_url)


@router.get("/auth/me")
def auth_me(authorization: Optional[str] = None):
    """Return decoded JWT claims for a token provided as Bearer. For debugging.

    Header: Authorization: Bearer <token>
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    parts = authorization.split()
    if parts[0].lower() != "bearer" or len(parts) != 2:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = parts[1]
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return JSONResponse(content={"claims": claims})
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
