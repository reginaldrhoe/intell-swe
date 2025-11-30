import React, { useState } from 'react'

function getApiBase() {
  try {
    const fromStorage = localStorage.getItem('ragpoc_api_base')
    if (fromStorage) return fromStorage.replace(/\/$/, '')
  } catch (e) {}
  if (typeof window !== 'undefined' && window.__API_URL__) return window.__API_URL__.replace(/\/$/, '')
  if (import.meta.env && import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL.replace(/\/$/, '')
  return 'http://localhost:8001'
}

function apiAgentEndpoint() {
  const base = getApiBase()
  const normalized = base.replace(/\/$/, '')
  return normalized.endsWith('/api') ? normalized + '/agents' : normalized + '/api/agents'
}

function apiTaskEndpoint() {
  const base = getApiBase()
  const normalized = base.replace(/\/$/, '')
  return normalized.endsWith('/api') ? normalized + '/tasks' : normalized + '/api/tasks'
}

function authHeaders() {
  const headers = { 'Content-Type': 'application/json' }
  try {
    const t = localStorage.getItem('ragpoc_token')
    if (t) headers['Authorization'] = 'Bearer ' + t
  } catch (e) {}
  return headers
}

export default function AgentTaskForm(){
  const [output, setOutput] = useState('')
  const [creating, setCreating] = useState(false)

  async function createAgent(e){
    e.preventDefault()
    const data = {
      name: e.target.agentName.value.trim(),
      role: e.target.agentRole.value.trim(),
      domain: e.target.agentDomain.value.trim(),
    }
    setCreating(true)
    try{
      const res = await fetch(apiAgentEndpoint(), { method: 'POST', headers: authHeaders(), body: JSON.stringify(data) })
      const text = await res.text()
      let parsed
      try{ parsed = JSON.parse(text) }catch{ parsed = text }
      setOutput('Agent Created: ' + JSON.stringify(parsed, null, 2))
    }catch(err){
      console.error(err)
      setOutput('Error creating agent: ' + String(err))
    }finally{ setCreating(false) }
  }

  async function createTask(e){
    e.preventDefault()
    const includeArtifacts = !!e.target.includeArtifacts?.checked
    const data = {
      title: e.target.taskTitle.value.trim(),
      description: e.target.taskDescription.value.trim(),
      access: e.target.taskAccessLevel.value,
      include_artifacts: includeArtifacts,
    }
    if (includeArtifacts) {
      data.artifact_paths = {
        junit_xml: ['artifacts/pytest.xml','artifacts/junit.xml'],
        coverage_xml: 'artifacts/coverage.xml',
        smoke_log: 'artifacts/smoke.log',
        e2e_log: 'artifacts/e2e.log',
      }
    }
    setCreating(true)
    try{
      const res = await fetch(apiTaskEndpoint(), { method: 'POST', headers: authHeaders(), body: JSON.stringify(data) })
      const text = await res.text()
      let parsed
      try{ parsed = JSON.parse(text) }catch{ parsed = text }
      setOutput('Task Created: ' + JSON.stringify(parsed, null, 2))

      // If the create response contains an id, poll the task endpoint
      try{
        const taskId = parsed && parsed.id ? parsed.id : null
        if(taskId){
          setOutput(prev => prev + '\n\nPolling task status (id=' + taskId + ')...')
          const base = getApiBase()
          let attempts = 0
          const maxAttempts = 60 // poll up to ~60s
          const iv = setInterval(async ()=>{
            attempts += 1
            try{
              const r = await fetch(base.replace(/\/$/, '') + '/api/tasks/' + taskId, { headers: authHeaders() })
              if(r.ok){
                const j = await r.json()
                // show status and any activities
                let out = 'Task: ' + JSON.stringify({id:j.id, title:j.title, status:j.status}, null, 2)
                if(Array.isArray(j.activities) && j.activities.length){
                  out += '\n\nActivities:\n' + j.activities.map(a => `${a.created_at} - ${a.content}`).join('\n\n')
                }
                setOutput(out)
                if(j.status && j.status !== 'pending' && j.status !== 'running'){
                  clearInterval(iv)
                }
              }
            }catch(pollErr){
              // ignore transient errors
            }
            if(attempts >= maxAttempts){
              clearInterval(iv)
              setOutput(prev => prev + '\n\nPolling timed out after ' + maxAttempts + ' attempts.')
            }
          }, 1000)
        }
      }catch(e){
        // noop
      }
    }catch(err){
      console.error(err)
      setOutput('Error creating task: ' + String(err))
    }finally{ setCreating(false) }
  }

  return (
    <div>
      <h2>Create Agent</h2>
      <form id="agentForm" onSubmit={createAgent}>
        <input name="agentName" type="text" placeholder="Agent Name" required />
        <input name="agentRole" type="text" placeholder="Role" required />
        <input name="agentDomain" type="text" placeholder="Domain" required />
        <button type="submit" disabled={creating}>Create Agent</button>
      </form>

      <h2 style={{marginTop:20}}>Create Task</h2>
      <form id="taskForm" onSubmit={createTask}>
        <input name="taskTitle" type="text" placeholder="Task Title" required />
        <textarea name="taskDescription" placeholder="Description" rows="4" required></textarea>
        <select name="taskAccessLevel">
          <option value="private">Private</option>
          <option value="shared">Shared</option>
        </select>
        <label style={{display:'block', marginTop:8}}>
          <input name="includeArtifacts" type="checkbox" defaultChecked /> Include artifact summary (artifacts/*)
        </label>
        <button type="submit" disabled={creating}>Create Task</button>
      </form>

      <div id="output" style={{marginTop:16, whiteSpace:'pre-wrap'}}>{output}</div>
    </div>
  )
}
