from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from .db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(128), unique=True, index=True, nullable=False)
    email = Column(String(256), unique=True, index=True, nullable=True)
    role = Column(String(32), default="user")


class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    description = Column(Text, nullable=True)
    public = Column(Boolean, default=False)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    status = Column(String(32), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IndexedCommit(Base):
    """Tracks the last successfully indexed commit for each repository/branch combination.
    
    Used for incremental git diff-based updates to Qdrant vector database.
    """
    __tablename__ = "indexed_commits"
    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String(512), nullable=False, index=True)
    branch = Column(String(256), nullable=False, index=True, default="main")
    commit_sha = Column(String(64), nullable=False)
    collection = Column(String(256), nullable=False, default="rag-poc")
    indexed_at = Column(DateTime(timezone=True), server_default=func.now())
    file_count = Column(Integer, nullable=True)  # Number of files indexed
    chunk_count = Column(Integer, nullable=True)  # Number of chunks created
