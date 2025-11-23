from prometheus_client import Counter, Gauge, generate_latest, CollectorRegistry
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import multiprocess
import os

registry = CollectorRegistry()

# Counters
INGEST_COUNTER = Counter("rag_ingest_total", "Total RAG ingests", registry=registry)
TASKS_ENQUEUED = Counter("mcp_tasks_enqueued_total", "Tasks enqueued to MCP", registry=registry)
AGENT_RUNS = Counter("mcp_agent_runs_total", "Agent runs", ["agent"], registry=registry)

# Gauges
QDRANT_POINTS = Gauge("qdrant_points", "Number of points in a qdrant collection", ["collection"], registry=registry)


def metrics_response():
    data = generate_latest(registry)
    return data, CONTENT_TYPE_LATEST
