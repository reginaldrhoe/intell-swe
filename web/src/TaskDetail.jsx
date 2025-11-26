import React, { useEffect, useState } from 'react'

function getApiBase(){
  try{ const s = localStorage.getItem('ragpoc_api_base'); if(s) return s.replace(/\/$/, '') }catch{}
  if(window.__API_URL__) return window.__API_URL__.replace(/\/$/, '')
  if(import.meta.env && import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL.replace(/\/$/, '')
  return 'http://localhost:8001'
}
function authHeaders(){
  const h = {'Content-Type':'application/json'}
  try{ const t = localStorage.getItem('ragpoc_token'); if(t) h['Authorization'] = 'Bearer ' + t }catch{}
  return h
}

export default function TaskDetail({id, onClose}){
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(false)

  async function fetchTask(){
    setLoading(true)
    try{
      const base = getApiBase()
      const res = await fetch(`${base.replace(/\/$/, '')}/api/tasks/${id}`, { headers: authHeaders() })
      if(res.ok){
        const j = await res.json()
        setTask(j)
      }
    }catch(e){ console.error(e) }
    finally{ setLoading(false) }
  }

  useEffect(()=>{
    let es = null
    let connectedSSE = false
    fetchTask()
    try{
      const base = getApiBase()
      const sUrl = `${base.replace(/\/$/, '')}/events/tasks/${id}`
      es = new EventSource(sUrl)
      es.onmessage = (e) => {
        try{
          const msg = JSON.parse(e.data)
          if(msg.type === 'status'){
            setTask(prev => prev ? {...prev, status: msg.status} : prev)
          } else if(msg.type === 'activity'){
            setTask(prev => {
              const acts = prev && Array.isArray(prev.activities) ? prev.activities.slice() : []
              const next = { id: prev?.id || id, title: prev?.title || '', description: prev?.description || '', status: prev?.status || '', created_at: prev?.created_at || '', activities: acts, agents: prev?.agents || {} }
              acts.push({ id: acts.length + 1, agent: msg.agent, content: msg.content, created_at: msg.created_at })
              next.activities = acts
              return next
            })
          } else if(msg.type === 'agent_status'){
            setTask(prev => {
              const agents = Object.assign({}, prev?.agents || {})
              agents[msg.agent] = msg.status
              const next = prev ? {...prev, agents} : { id, title:'', description:'', status:'', created_at:'', activities:[], agents }
              return next
            })
          }
        }catch(err){
          // ignore parse errors
        }
      }
      es.onerror = (err) => {
        try{ es.close() }catch(e){}
      }
      connectedSSE = true
    }catch(err){
      // fall back to polling if EventSource creation fails
      const iv = setInterval(fetchTask, 2000)
      return ()=> clearInterval(iv)
    }

    return ()=>{
      try{ if(es) es.close() }catch(e){}
    }
  }, [id])

  return (
    <div style={{position:'fixed', right:20, top:80, width:520, maxHeight:'70%', overflow:'auto', padding:12, background:'#fff', border:'1px solid #ddd', boxShadow:'0 4px 12px rgba(0,0,0,0.08)'}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h4 style={{margin:0}}>Task {id}</h4>
        <div><button onClick={onClose}>Close</button></div>
      </div>
      {loading && <div>Loading...</div>}
      {task && (
        <div>
          <p><strong>{task.title}</strong></p>
          <p style={{whiteSpace:'pre-wrap'}}>{task.description}</p>
          <p style={{display:'flex',alignItems:'center',gap:8}}><em>Status: {task.status}</em>{task.agents && Object.values(task.agents).some(s=>s==='running') && <span style={{padding:'4px 8px',background:'#eef',borderRadius:6}}>Running…</span>}</p>
          {task.agents && (
            <div style={{marginBottom:8}}>
              <strong>Agent Status</strong>
              <div style={{display:'flex',gap:8,flexWrap:'wrap',marginTop:6}}>
                {Object.keys(task.agents).map(name => (
                  <div key={name} style={{padding:'6px 8px',background:'#fafafa',border:'1px solid #eee',borderRadius:6}}>
                    <div style={{fontSize:12}}>{name}</div>
                    <div style={{fontSize:12,color: task.agents[name]==='running' ? '#0a66ff' : (task.agents[name]==='failed' ? '#d9534f' : '#2d6a2d')}}>{task.agents[name]}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          <h5>Activities</h5>
          {task.activities && task.activities.length ? (
            task.activities.map(a=> (
              <div key={a.id} style={{marginBottom:12, padding:8, background:'#f9f9f9', borderRadius:6}}>
                <div style={{fontSize:12,color:'#666'}}>{a.created_at}</div>
                <div style={{whiteSpace:'pre-wrap', marginTop:6}}>{a.content}</div>
              </div>
            ))
          ) : (<div style={{color:'#666'}}>No activities yet.</div>)}
        </div>
      )}
    </div>
  )
}
