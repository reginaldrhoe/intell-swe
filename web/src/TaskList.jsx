import React, { useEffect, useState } from 'react'
import TaskDetail from './TaskDetail'

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

export default function TaskList(){
  const [tasks, setTasks] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)

  async function fetchTasks(){
    setLoading(true)
    try{
      const base = getApiBase()
      const res = await fetch(base.replace(/\/$/, '') + '/api/tasks', { headers: authHeaders() })
      if(res.ok){
        const j = await res.json()
        setTasks(j)
      }
    }catch(e){
      console.error(e)
    }finally{ setLoading(false) }
  }

  useEffect(()=>{
    fetchTasks()
    const iv = setInterval(fetchTasks, 5000)
    return ()=> clearInterval(iv)
  }, [])

  return (
    <div>
      <h3>Tasks</h3>
      {loading && <div>Loading...</div>}
      <ul style={{maxHeight:300, overflow:'auto', paddingLeft:10}}>
        {tasks.map(t=> (
          <li key={t.id} style={{marginBottom:8, cursor:'pointer'}} onClick={()=>setSelected(t.id)}>
            <strong>{t.title}</strong> <em style={{color:'#666'}}>{t.status}</em>
            <div style={{fontSize:12,color:'#444'}}>{t.created_at}</div>
          </li>
        ))}
      </ul>
      {selected && <TaskDetail id={selected} onClose={()=>setSelected(null)} />}
    </div>
  )
}
