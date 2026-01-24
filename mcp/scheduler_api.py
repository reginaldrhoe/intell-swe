
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List
import json
from mcp.db import SessionLocal
from mcp import models
from mcp.api import get_db, get_current_user

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])

@router.get("/tasks")
def list_scheduled_tasks(db: Session = Depends(get_db), user = Depends(get_current_user)):
    tasks = db.query(models.ScheduledTask).order_by(models.ScheduledTask.id.desc()).all()
    out = []
    for t in tasks:
        out.append({
            "id": t.id,
            "name": t.name,
            "schedule_type": t.schedule_type,
            "schedule_value": t.schedule_value,
            "task_payload": t.task_payload,
            "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
            "next_run_at": t.next_run_at.isoformat() if t.next_run_at else None,
            "is_active": t.is_active,
            "created_at": t.created_at.isoformat() if t.created_at else None
        })
    return out

@router.post("/tasks")
def create_scheduled_task(payload: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Create a new scheduled task.
    Payload: {
        "name": "Nightly Build",
        "schedule_type": "interval" | "cron",
        "schedule_value": "3600" | "0 0 * * *",
        "task_payload": { "title": "Run tests", ... }
    }
    """
    name = payload.get("name")
    sType = payload.get("schedule_type", "interval")
    sValue = payload.get("schedule_value")
    tPayload = payload.get("task_payload")

    if not name or not sValue or not tPayload:
        raise HTTPException(status_code=400, detail="Missing required fields (name, schedule_value, task_payload)")

    # Normalize task payload to string if it's a dict
    if isinstance(tPayload, dict):
        tPayload = json.dumps(tPayload)

    st = models.ScheduledTask(
        name=name,
        schedule_type=sType,
        schedule_value=sValue,
        task_payload=tPayload,
        is_active=True
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    return {"id": st.id, "name": st.name}

@router.delete("/tasks/{task_id}")
def delete_scheduled_task(task_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(models.ScheduledTask).filter(models.ScheduledTask.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    
    db.delete(t)
    db.commit()
    return {"status": "deleted", "id": task_id}
