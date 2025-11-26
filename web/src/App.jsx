import React, {useEffect, useState} from 'react'
import LoginButton from './LoginButton'
import AgentTaskForm from './AgentTaskForm'
import TaskList from './TaskList'
import Settings from './Settings'
import './styles.css'

const API_BASE = window.__API_URL__ || (import.meta.env.VITE_API_URL || 'http://localhost:8001')

export default function App(){
  const [agents, setAgents] = useState(null)
  const [token, setToken] = useState(() => {
    try { return localStorage.getItem('ragpoc_token') }
    catch { return null }
  })
  const [apiBase, setApiBase] = useState(() => {
    try { return localStorage.getItem('ragpoc_api_base') || (window.__API_URL__ ? window.__API_URL__.replace(/\/$/, '') : (import.meta.env.VITE_API_URL || 'http://localhost:8000')) }
    catch { return 'http://localhost:8000' }
  })
  const [apiInput, setApiInput] = useState(apiBase)
  const [tokenInput, setTokenInput] = useState(token || '')

  useEffect(()=>{
    // capture token from URL fragment
    const hash = window.location.hash.substring(1)
    if(hash){
      const params = new URLSearchParams(hash)
      const t = params.get('access_token')
      if(t){
        localStorage.setItem('ragpoc_token', t)
        setToken(t)
        history.replaceState(null, '', window.location.pathname + window.location.search)
      }
    }
  }, [])

  function saveApiBase(){
    const normalized = (apiInput || '').replace(/\/$/, '')
    try{ localStorage.setItem('ragpoc_api_base', normalized) } catch(e){}
    setApiBase(normalized)
    setApiInput(normalized)
  }

  function saveToken(){
    try{ localStorage.setItem('ragpoc_token', tokenInput) }catch(e){}
    setToken(tokenInput)
  }

  function clearToken(){
    try{ localStorage.removeItem('ragpoc_token') }catch(e){}
    setToken(null)
    setTokenInput('')
  }

  useEffect(()=>{
    async function fetchAgents(){
      try{
        const headers = {}
        if(token) headers['Authorization'] = 'Bearer ' + token
        const base = (apiBase || API_BASE).replace(/\/$/, '')
        const res = await fetch(base + '/api/agents', {headers})
        if(res.status === 401){
          setAgents({error: 'Unauthorized'})
          return
        }
        const data = await res.json()
        setAgents(data)
      }catch(e){
        setAgents({error: String(e)})
      }
    }
    fetchAgents()
  }, [token, apiBase])

  // Health check for backend
  const [health, setHealth] = useState({status: 'unknown', ok: false})
  useEffect(()=>{
    let mounted = true
    async function check(){
      const base = (apiBase || API_BASE).replace(/\/$/, '')
      try{
        const res = await fetch(base + '/health')
        if(!mounted) return
        if(res.ok){
          setHealth({status: 'ok', ok: true})
        } else {
          setHealth({status: 'error', ok: false})
        }
      }catch(e){
        if(!mounted) return
        setHealth({status: 'down', ok: false})
      }
    }
    check()
    const t = setInterval(check, 10000)
    return ()=>{ mounted = false; clearInterval(t) }
  }, [apiBase])

  function logout(){
    localStorage.removeItem('ragpoc_token')
    setToken(null)
  }

  return (
    <div className="container">
      <h1>RAG-POC Frontend (Vite)</h1>

      <div style={{display:'flex',gap:8,alignItems:'center',justifyContent:'center',marginBottom:12}}>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <label style={{fontSize:12,opacity:0.8}}>API Base</label>
          <input value={apiInput} onChange={(e)=>setApiInput(e.target.value)} style={{width:340}} />
          <button onClick={saveApiBase}>Save</button>
        </div>
      </div>

      <div style={{display:'flex',gap:8,alignItems:'center',justifyContent:'center',marginBottom:8}}>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <label style={{fontSize:12,opacity:0.8}}>Token</label>
          <input value={tokenInput} onChange={(e)=>setTokenInput(e.target.value)} style={{width:340}} placeholder="paste bearer token here" />
          <button onClick={saveToken}>Save</button>
          <button onClick={clearToken} style={{marginLeft:6}}>Clear</button>
        </div>
      </div>

      <div style={{display:'flex',justifyContent:'center',gap:8,alignItems:'center',marginBottom:8}}>
        <LoginButton />
        {token && <button onClick={logout}>Logout</button>}
        <div style={{marginLeft:16, display:'flex', alignItems:'center', gap:8}}>
          <strong style={{fontSize:12}}>Backend:</strong>
          <span style={{padding:'4px 8px',borderRadius:6, background: health.ok ? '#dff0d8' : '#ffe6e6', color: health.ok ? '#2d6a2d' : '#7a1f1f'}}>
            {health.ok ? 'OK' : (health.status === 'unknown' ? 'Unknown' : 'Down')}
          </span>
        </div>
      </div>

      <div className="app-grid" style={{alignItems:'flex-start'}}>
        <div style={{flex:1, minWidth:520}}>
          <AgentTaskForm />
        </div>
        <div style={{width:420}}>
          <TaskList />
        </div>
      </div>

      <div style={{marginTop:24}}>
        <Settings token={token} apiBase={apiBase} />
      </div>
    </div>
  )
}
