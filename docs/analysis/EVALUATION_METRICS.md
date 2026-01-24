# Evaluation Metrics — rag-poc (MVP v2.3.0)

<img src="../docs/Logo%20design%20featurin.png" alt="Logo" width="200">

Scope
- Documents quantitative and qualitative metrics for assessing framework performance, agent effectiveness, system reliability, and user satisfaction.

Audience
- Developers, SREs, product managers, and stakeholders evaluating system health and ROI.

---

## 1. System Performance Metrics

### 1.1 Throughput
- **Tasks per Hour**: Count of successfully completed tasks per hour (`TASKS_ENQUEUED`, `TASKS_COMPLETED` delta).
- **Agent Invocations per Minute**: Total agent executions across all tasks (`AGENT_RUNS` counter rate).
- **Concurrent Task Capacity**: Maximum simultaneous running tasks before lock contention or resource saturation.

### 1.2 Latency
- **Task End-to-End Latency**: Time from `POST /run-agents` to `status=done` (p50, p95, p99).
- **Lock Acquisition Time**: Duration from first lock attempt to successful acquisition (sentinel-based or metric).
- **Agent Response Time**: Per-agent duration from invocation to result (`__coordination_metrics__["agents"][agent]["duration"]`).
- **Vector Search Latency**: Qdrant query response time for semantic retrieval (log or instrument Qdrant client).

### 1.3 Resource Utilization
- **CPU Usage**: Per-container CPU % (via `docker stats` or Prometheus node exporter).
- **Memory Consumption**: Heap/RSS for `mcp`, `worker`, `qdrant`, `mysql` containers.
- **Redis Connection Pool**: Active/idle connections, evictions, command latency.
- **Qdrant Index Size**: Vector count, storage bytes, search QPS.

---

## 2. Agent Effectiveness Metrics

### 2.1 Output Quality (Post-Feedback)
- **Approval Rate**: `SUM(feedback.verdict='approve') / SUM(feedback.verdict IN ('approve','reject'))` per agent, per time window.
- **Average User Rating**: Mean of `feedback.rating` (0–5 scale) per agent.
- **Correction Frequency**: Percentage of outputs receiving non-empty `correction_text`.
- **Answer Relevance Score**: Semantic similarity between user query and agent response (optional embeddings-based scoring).

### 2.2 Coordination Efficiency
- **Parallel Efficiency Ratio**: `sum_agent_durations / wall_time` (ideal ≈ agent_count for perfect parallelism; >1 indicates overlap).
- **Delegation Depth**: Average number of phases in delegation workflows.
- **Context Propagation Success**: Percentage of delegated tasks successfully receiving prior phase outputs.

### 2.3 Artifact Intelligence
- **Artifact Ingestion Rate**: Count of JUnit/coverage/log artifacts processed per day.
- **Artifact-Driven Insights**: Percentage of agent outputs referencing artifact summaries.
- **False Positive Rate**: Manual review of artifact-flagged issues vs actual bugs.

---

## 3. Reliability & Availability Metrics

### 3.1 Duplicate Protection
- **Lock Conflict Rate**: `LOCK_CONFLICT` events / total `run-agents` requests (target <5% under normal load).
- **Lock Leak Incidents**: Count of locks held beyond TTL without release (monitor orphaned Redis keys).
- **DB Fallback Invocations**: Atomic UPDATE fallback usage when Redis unavailable.

### 3.2 Uptime & Failures
- **Service Availability**: Uptime % per container (`mcp`, `worker`, `mysql`, `redis`, `qdrant`) over 30-day window.
- **Task Failure Rate**: `SUM(status='failed') / SUM(status IN ('done','failed'))`.
- **Agent Exception Rate**: Count of agent tasks raising exceptions vs successful completions.
- **Vector Index Corruption**: Qdrant integrity checks, rebuilds required.

### 3.3 Recovery Time
- **Mean Time to Recovery (MTTR)**: Average duration from incident detection to service restoration.
- **Auto-Restart Success Rate**: Vite persistent script restart success % (if restart cap not exceeded).

---

## 4. Data & Ingestion Metrics

### 4.1 Repository Synchronization
- **Incremental Sync Success Rate**: Percentage of git diff ingestions completing without fallback to full reindex.
- **Vector Chunk Staleness**: Age distribution of embeddings vs latest commit (detect drift).
- **Deleted File Cleanup**: Orphaned vector count after file deletions (monitor tombstone/soft-delete accuracy).

### 4.2 Embedding Quality
- **Embedding Dimension Consistency**: Verify all vectors match expected dimensionality.
- **Semantic Drift**: Cosine similarity between re-embedded identical text over time (detect model/config changes).
- **Search Recall@K**: For known queries, % of expected documents returned in top K results.

---

## 5. User Experience Metrics

### 5.1 Interaction Patterns
- **Active Users per Day/Week**: Unique `user_id` counts submitting tasks or feedback.
- **Task Submission Rate**: Daily/weekly task creation trends.
- **Feedback Submission Rate**: Percentage of completed tasks receiving user feedback.

### 5.2 Satisfaction Signals
- **Net Promoter Score (NPS)**: Optional survey-based metric (not instrumented in 2.3.0).
- **Repeat Usage Rate**: Percentage of users creating >1 task per week.
- **Session Duration**: Time from first UI load to last interaction (frontend analytics if instrumented).

### 5.3 Adoption & Retention
- **Feature Usage Breakdown**: Counts per endpoint (`/api/tasks`, `/run-agents`, `/admin/ingest`, `/feedback`).
- **Churn Rate**: Users inactive >30 days after initial use.

---

## 6. Security & Compliance Metrics

### 6.1 Access Control
- **RBAC Enforcement Rate**: Percentage of protected endpoints correctly rejecting unauthorized requests (audit logs).
- **Token Expiration Events**: Count of expired/revoked tokens (if TTL tracking added).
- **Failed Authentication Attempts**: Rate of 401/403 responses per endpoint.

### 6.2 Data Sovereignty
- **Local vs External API Calls**: Ratio of mock vs real OpenAI invocations (privacy control).
- **Data Residency Compliance**: Percentage of data stored in compliant regions (requires geo-aware storage).
- **Encryption Coverage**: Percentage of sensitive fields encrypted at rest (not implemented in 2.3.0).

---

## 7. Cost Metrics

### 7.1 Infrastructure
- **Compute Cost per Task**: CPU/memory cost amortized over task count.
- **Storage Growth Rate**: MB/day for MySQL, Qdrant, Redis, artifact storage.
- **External API Cost**: OpenAI token usage and billing (when not using mock).

### 7.2 Operational Efficiency
- **Cost per Agent Invocation**: Total infrastructure cost / `AGENT_RUNS`.
- **Resource Waste**: Idle container time, unused vector capacity.

---

## 8. Observability & Instrumentation

### 8.1 Prometheus Metrics Exposed
- `TASKS_ENQUEUED` (counter): Total tasks created.
- `AGENT_RUNS` (counter): Total agent invocations.
- `INGEST_COUNTER` (counter): Ingestion operations (full/incremental).
- `ARTIFACT_INGEST_BATCHES` (counter, planned): Artifact processing count.
- `INCREMENTAL_SYNC_COMMITS` (counter, planned): Commit-based sync executions.
- `VECTOR_CHUNKS_ACTIVE` (gauge, planned): Non-tombstoned vector count.
- `agent_duration_seconds` (histogram, planned): Per-agent execution time.
- `delegation_phase_seconds` (histogram, planned): Per-phase timings.
- `agent_feedback_total{agent, verdict}` (counter, planned): Feedback events.
- `agent_rating_average{agent}` (gauge, planned): Rolling average rating.
- `agent_weight{agent}` (gauge, planned): Adaptive agent weights.

### 8.2 Logging & Tracing
- **Structured JSON Logs**: Include `task_id`, `agent_name`, `timestamp`, `status` for correlation.
- **Trace Correlation IDs**: Link SSE events, DB writes, and Redis ops per task.
- **Error Rate by Category**: Parse log levels (ERROR, WARN) and categorize (lock timeout, DB connection, agent exception).

### 8.3 Sentinel Files (Smoke Test Validation)
- `/tmp/run_agents_entered.log`: Handler entry count (detect request volume).
- `/tmp/run_agents_lock_acquired.log`: Lock acquisition method distribution (async vs sync).
- `/tmp/run_agents_lock_conflict.log`: Conflict count per task_id (duplicate detection accuracy).

---

## 9. Baseline & Target Values (Recommended)

### Performance Targets (Single-Node Dev)
- Task end-to-end latency (p95): <10s for simple tasks, <60s for complex multi-agent workflows.
- Agent response time (p95): <5s per agent (stub/mock mode).
- Parallel efficiency ratio: >0.8 for 6-agent runs (indicates minimal serialization).

### Reliability Targets
- Service availability: >99% uptime for `mcp`, `mysql`, `redis`, `qdrant` (30-day window).
- Task failure rate: <2% (excluding user input errors).
- Lock conflict rate: <5% under concurrent load.

### Quality Targets (Post-Feedback Implementation)
- Agent approval rate: >70% for established agents.
- Average user rating: >3.5/5.0.
- Feedback submission rate: >30% of completed tasks.

### Data Targets
- Incremental sync success rate: >90% (fallback to full reindex <10%).
- Vector search recall@10: >80% for known queries.
- Artifact ingestion lag: <1 hour from pytest completion to agent availability.

---

## 10. Measurement Tools & Queries

### Prometheus Queries
- Task throughput (hourly): `rate(TASKS_ENQUEUED[1h])`
- Agent latency p95: `histogram_quantile(0.95, rate(agent_duration_seconds_bucket[5m]))`
- Lock conflict rate: `rate(lock_conflict_total[5m]) / rate(run_agents_requests_total[5m])`

### SQL Queries
- Recent approval rate per agent:
```sql
SELECT ao.agent_name,
       SUM(CASE WHEN af.verdict='approve' THEN 1 ELSE 0 END) * 100.0 /
         NULLIF(SUM(CASE WHEN af.verdict IN ('approve','reject') THEN 1 ELSE 0 END), 0) AS approval_pct
FROM AgentOutput ao
JOIN AgentFeedback af ON af.agent_output_id = ao.id
WHERE af.created_at >= NOW() - INTERVAL 7 DAY
GROUP BY ao.agent_name;
```
- Task latency distribution:
```sql
SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY TIMESTAMPDIFF(SECOND, created_at, updated_at)) AS p50,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY TIMESTAMPDIFF(SECOND, created_at, updated_at)) AS p95
FROM Task
WHERE status = 'done' AND updated_at >= NOW() - INTERVAL 1 DAY;
```

### Sentinel File Analysis
```powershell
# Lock acquisition methods
docker exec $(docker compose ps -q mcp) cat /tmp/run_agents_lock_acquired.log | Select-String "async|sync" | Group-Object | Select-Object Count, Name

# Conflict rate
$entered = (docker exec $(docker compose ps -q mcp) cat /tmp/run_agents_entered.log | Measure-Object -Line).Lines
$conflicts = (docker exec $(docker compose ps -q mcp) cat /tmp/run_agents_lock_conflict.log | Measure-Object -Line).Lines
Write-Host "Conflict rate: $($conflicts/$entered * 100)%"
```

---

## 11. Continuous Improvement Cycle

### Monthly Review
- Compare current metrics vs baselines and targets.
- Identify top 3 bottlenecks (latency spikes, low approval agents, resource saturation).
- Prioritize fixes (e.g., index tuning, agent prompt refinement, capacity scaling).

### Quarterly Objectives
- Agent approval rate improvement: +5% per quarter.
- Task throughput increase: +20% with same resource allocation.
- Reduce MTTR: -10% via better alerting and runbook automation.

### Experiment Tracking
- A/B test prompt variations: measure approval rate delta.
- Canary new agent versions: monitor exception rate and latency before rollout.
- Shadow mode for new features: compare outputs without affecting production.

---

## 12. Gaps & Future Instrumentation (v2.3.0)

### Not Yet Implemented
- User feedback capture (`POST /feedback`, `AgentFeedback` table).
- Adaptive agent weighting and reordering.
- Detailed per-agent Prometheus histograms (`agent_duration_seconds`).
- Embedding drift detection and auto-reindex triggers.
- Cost tracking integration (cloud provider billing APIs).
- Distributed tracing (Jaeger/Zipkin span correlation).

### Planned Next Phase
- Feedback loop infrastructure (Phase 1: capture, Phase 2: aggregation, Phase 3: adaptation).
- Enhanced Prometheus exporters for agent/delegation metrics.
- Automated anomaly detection and alerting (SLO/SLI definitions).
- Dashboard templates (Grafana JSON) for common metric views.

---

## Contact & Ownership
- File: `docs/EVALUATION_METRICS.md`
- Maintained by: Engineering team
- Last updated: November 30, 2025 (v2.3.0)
