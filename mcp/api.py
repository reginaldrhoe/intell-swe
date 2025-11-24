from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Generator, Optional
from .db import SessionLocal, init_db
from . import models
from sqlalchemy.orm import Session
import os
import threading
import json
import urllib.request
import urllib.error


router = APIRouter(prefix="/api")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init():
    # Ensure DB tables exist
    init_db()


def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Simple token -> user mapping for MVP. In production, wire OAuth SSO.

    Expected header: Authorization: Bearer <username>
    This helper will create a user record if not present for quick testing.
    """
    if authorization is None:
        # return an anonymous demo user
        user = db.query(models.User).filter(models.User.username == "demo").first()
        if not user:
            user = models.User(username="demo", email="demo@example.com", role="admin")
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    # parse very small bearer token format
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        # treat token as username for MVP
        user = db.query(models.User).filter(models.User.username == token).first()
        if not user:
            user = models.User(username=token, email=f"{token}@example.com", role="staff")
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    raise HTTPException(status_code=401, detail="Invalid authorization header")


@router.on_event("startup")
def _on_startup():
    init()


@router.get("/agents")
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(models.Agent).all()
    return [ {"id": a.id, "name": a.name, "description": a.description, "owner_id": a.owner_id} for a in agents ]


@router.post("/agents")
def create_agent(payload: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    name = payload.get("name")
    description = payload.get("description")
    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name'")
    a = models.Agent(name=name, description=description or "", owner_id=user.id)
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"id": a.id, "name": a.name}


@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db), user = Depends(get_current_user)):
    tasks = db.query(models.Task).filter(models.Task.owner_id == user.id).all()
    return [ {"id": t.id, "title": t.title, "status": t.status, "created_at": t.created_at.isoformat()} for t in tasks ]


@router.post("/tasks")
def create_task(payload: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    title = payload.get("title")
    description = payload.get("description")
    agent_id = payload.get("agent_id")
    if not title:
        raise HTTPException(status_code=400, detail="Missing 'title'")
    t = models.Task(title=title, description=description or "", owner_id=user.id, agent_id=agent_id)
    db.add(t)
    db.commit()
    db.refresh(t)
    result = {"id": t.id, "title": t.title, "status": t.status}

    # Fire-and-forget: try to notify the run endpoint so agents begin processing.
    # We do this in a background thread via a simple HTTP POST to /run-agents
    def _notify_run_agents(task_payload):
        try:
            base = os.getenv('INTERNAL_API_BASE', 'http://localhost:8001').rstrip('/')
            url = base + '/run-agents'
            data = json.dumps(task_payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method='POST')
            with urllib.request.urlopen(req, timeout=10) as resp:
                # consume response, but don't block caller
                try:
                    resp.read()
                except Exception:
                    pass
        except urllib.error.HTTPError as e:
            # log to stdout for container logs
            try:
                print(f"_notify_run_agents: http error: {e.code} {e.reason}")
            except Exception:
                pass
        except Exception as e:
            try:
                print(f"_notify_run_agents: failed: {e}")
            except Exception:
                pass

    try:
        task_payload = {"id": t.id, "title": t.title, "description": t.description, "agent_id": t.agent_id}
        th = threading.Thread(target=_notify_run_agents, args=(task_payload,), daemon=True)
        th.start()
    except Exception:
        pass

    return result


@router.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    t = db.query(models.Task).filter(models.Task.id == task_id, models.Task.owner_id == user.id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")

    activities = db.query(models.Activity).filter(models.Activity.task_id == t.id).order_by(models.Activity.created_at.asc()).all()
    acts = [ {"id": a.id, "agent_id": a.agent_id, "content": a.content, "created_at": a.created_at.isoformat()} for a in activities ]

    return {"id": t.id, "title": t.title, "description": t.description, "status": t.status, "created_at": t.created_at.isoformat(), "activities": acts}
