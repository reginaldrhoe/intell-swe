
import React, { useState, useEffect } from 'react'
import './styles.css'

export default function ScheduledTasks({ token, apiBase }) {
    const [tasks, setTasks] = useState([])
    const [error, setError] = useState(null)

    // Form state
    const [name, setName] = useState('')
    const [scheduleType, setScheduleType] = useState('interval')
    const [scheduleValue, setScheduleValue] = useState('3600')
    const [taskPayloadStr, setTaskPayloadStr] = useState('{\n  "title": "Recurring Task",\n  "description": "Auto-generated task",\n  "agent_id": null\n}')
    const [loading, setLoading] = useState(false)

    const BASE = (apiBase || '').replace(/\/$/, '')

    useEffect(() => {
        fetchTasks()
    }, [token, apiBase])

    async function fetchTasks() {
        if (!token) return
        try {
            const res = await fetch(`${BASE}/api/scheduler/tasks`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            if (res.ok) {
                const data = await res.json()
                setTasks(data)
                setError(null)
            } else {
                setError(`Failed to load tasks: ${res.status}`)
            }
        } catch (e) {
            setError(String(e))
        }
    }

    async function handleCreate() {
        setLoading(true)
        setError(null)
        try {
            // Validate JSON payload
            let payloadObj
            try {
                payloadObj = JSON.parse(taskPayloadStr)
            } catch (e) {
                throw new Error("Invalid JSON in Task Payload")
            }

            const res = await fetch(`${BASE}/api/scheduler/tasks`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    name,
                    schedule_type: scheduleType,
                    schedule_value: scheduleValue,
                    task_payload: payloadObj
                })
            })

            if (res.ok) {
                setName('')
                setTaskPayloadStr('{\n  "title": "Recurring Task",\n  "description": "Auto-generated task",\n  "agent_id": null\n}')
                fetchTasks()
            } else {
                const err = await res.json()
                setError(err.detail || 'Failed to create task')
            }
        } catch (e) {
            setError(String(e))
        } finally {
            setLoading(false)
        }
    }

    async function handleDelete(id) {
        if (!confirm("Are you sure you want to delete this scheduled task?")) return
        try {
            const res = await fetch(`${BASE}/api/scheduler/tasks/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            })
            if (res.ok) {
                fetchTasks()
            } else {
                setError("Failed to delete task")
            }
        } catch (e) {
            setError(String(e))
        }
    }

    if (!token) return null

    return (
        <div className="card">
            <h2>Scheduled Tasks (Automation)</h2>

            {error && <div className="error">{error}</div>}

            <div style={{ marginBottom: 20, padding: 12, background: '#f8f9fa', borderRadius: 8 }}>
                <h3>Create Schedule</h3>
                <div style={{ display: 'flex', gap: 10, marginBottom: 8 }}>
                    <input
                        placeholder="Schedule Name (e.g. Nightly Build)"
                        value={name}
                        onChange={e => setName(e.target.value)}
                        style={{ flex: 1 }}
                    />
                    <select value={scheduleType} onChange={e => setScheduleType(e.target.value)}>
                        <option value="interval">Interval (Seconds)</option>
                        <option value="cron">Cron Expression</option>
                    </select>
                    <input
                        placeholder={scheduleType === 'interval' ? "3600" : "0 0 * * *"}
                        value={scheduleValue}
                        onChange={e => setScheduleValue(e.target.value)}
                        style={{ width: 120 }}
                    />
                </div>
                <textarea
                    value={taskPayloadStr}
                    onChange={e => setTaskPayloadStr(e.target.value)}
                    rows={5}
                    style={{ width: '100%', fontFamily: 'monospace', fontSize: 13 }}
                    placeholder="Task JSON Payload"
                />
                <button onClick={handleCreate} disabled={loading} style={{ marginTop: 8 }}>
                    {loading ? 'Creating...' : 'Schedule Task'}
                </button>
            </div>

            <div className="task-list">
                {tasks.map(t => (
                    <div key={t.id} className="task-item" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <strong>{t.name}</strong>
                            <span style={{ fontSize: 12, color: '#666', marginLeft: 8 }}>
                                ({t.schedule_type}: {t.schedule_value})
                            </span>
                            <div style={{ fontSize: 12, marginTop: 4 }}>
                                Next Run: {t.next_run_at ? new Date(t.next_run_at).toLocaleString() : 'Pending'} |
                                Last Run: {t.last_run_at ? new Date(t.last_run_at).toLocaleString() : 'Never'}
                            </div>
                        </div>
                        <button onClick={() => handleDelete(t.id)} className="btn-small danger">Delete</button>
                    </div>
                ))}
                {tasks.length === 0 && <div style={{ color: '#888', fontStyle: 'italic' }}>No scheduled tasks found.</div>}
            </div>
        </div>
    )
}
