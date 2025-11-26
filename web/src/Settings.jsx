import React, {useEffect, useState} from 'react'

const API_BASE = window.__API_URL__ || (import.meta.env.VITE_API_URL || 'http://localhost:8001')

export default function Settings({token, apiBase}){
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState(null)

  // Form state
  const [collection, setCollection] = useState('')
  const [repos, setRepos] = useState([])

  useEffect(()=>{
    fetchConfig()
  }, [token, apiBase])

  async function fetchConfig(){
    setLoading(true)
    setError(null)
    try{
      const headers = {}
      if(token) headers['Authorization'] = 'Bearer ' + token
      const base = (apiBase || API_BASE).replace(/\/$/, '')
      const res = await fetch(base + '/rag-config', {headers})
      if(!res.ok){
        throw new Error(`Failed to fetch config: ${res.status}`)
      }
      const data = await res.json()
      const cfg = data.config || {}
      setConfig(cfg)
      setCollection(cfg.collection || 'rag-poc')
      setRepos(cfg.repos || [])
    }catch(e){
      setError(String(e))
    }finally{
      setLoading(false)
    }
  }

  async function saveConfig(){
    setSaving(true)
    setSaveStatus(null)
    try{
      const headers = {'Content-Type': 'application/json'}
      if(token) headers['Authorization'] = 'Bearer ' + token
      const base = (apiBase || API_BASE).replace(/\/$/, '')
      const body = {
        collection,
        repos: repos.filter(r => r.url && r.url.trim())
      }
      const res = await fetch(base + '/rag-config', {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
      })
      if(!res.ok){
        throw new Error(`Failed to save config: ${res.status}`)
      }
      const data = await res.json()
      setConfig(data.config)
      setSaveStatus('✓ Saved successfully')
      setTimeout(()=>setSaveStatus(null), 3000)
    }catch(e){
      setSaveStatus('✗ Error: ' + String(e))
    }finally{
      setSaving(false)
    }
  }

  function addRepo(){
    setRepos([...repos, {
      url: '',
      auto_ingest: true,
      collection: collection,
      branches: ['main']
    }])
  }

  function removeRepo(idx){
    setRepos(repos.filter((_, i) => i !== idx))
  }

  function updateRepo(idx, field, value){
    const updated = [...repos]
    updated[idx] = {...updated[idx], [field]: value}
    setRepos(updated)
  }

  function updateRepoBranches(idx, branchesStr){
    const branches = branchesStr.split(',').map(b => b.trim()).filter(b => b)
    updateRepo(idx, 'branches', branches)
  }

  if(loading) return <div style={{padding:16}}>Loading RAG configuration...</div>
  if(error) return <div style={{padding:16,color:'#d33'}}>Error: {error}</div>

  return (
    <div style={{padding:16, border:'1px solid #ddd', borderRadius:8, background:'#f9f9f9'}}>
      <h2 style={{marginTop:0}}>RAG Configuration</h2>
      <p style={{fontSize:13,opacity:0.8,marginTop:-8}}>
        Configure which repositories and branches to ingest for RAG. Changes trigger automatic re-ingestion.
      </p>

      <div style={{marginBottom:16}}>
        <label style={{display:'block',fontWeight:'bold',marginBottom:4}}>Collection Name</label>
        <input
          type="text"
          value={collection}
          onChange={(e)=>setCollection(e.target.value)}
          placeholder="rag-poc"
          style={{width:'100%',padding:8,fontSize:14}}
        />
        <small style={{opacity:0.7}}>Qdrant collection name for vector storage</small>
      </div>

      <div style={{marginBottom:16}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
          <label style={{fontWeight:'bold'}}>Repositories</label>
          <button onClick={addRepo} style={{padding:'4px 12px',fontSize:13}}>+ Add Repo</button>
        </div>

        {repos.length === 0 && (
          <div style={{padding:16,background:'#fff',border:'1px dashed #ccc',borderRadius:4,textAlign:'center',opacity:0.6}}>
            No repositories configured. Click "+ Add Repo" to add one.
          </div>
        )}

        {repos.map((repo, idx) => (
          <div key={idx} style={{padding:12,background:'#fff',border:'1px solid #ddd',borderRadius:6,marginBottom:12}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
              <strong style={{fontSize:14}}>Repository {idx + 1}</strong>
              <button onClick={()=>removeRepo(idx)} style={{padding:'2px 8px',fontSize:12,background:'#d33',color:'#fff'}}>Remove</button>
            </div>

            <div style={{marginBottom:8}}>
              <label style={{display:'block',fontSize:13,marginBottom:4}}>Repository URL</label>
              <input
                type="text"
                value={repo.url || ''}
                onChange={(e)=>updateRepo(idx, 'url', e.target.value)}
                placeholder="https://github.com/owner/repo.git"
                style={{width:'100%',padding:6,fontSize:13}}
              />
            </div>

            <div style={{marginBottom:8}}>
              <label style={{display:'block',fontSize:13,marginBottom:4}}>Branches (comma-separated)</label>
              <input
                type="text"
                value={(repo.branches || []).join(', ')}
                onChange={(e)=>updateRepoBranches(idx, e.target.value)}
                placeholder="main, develop"
                style={{width:'100%',padding:6,fontSize:13}}
              />
            </div>

            <div style={{marginBottom:8}}>
              <label style={{display:'block',fontSize:13,marginBottom:4}}>Collection (optional override)</label>
              <input
                type="text"
                value={repo.collection || ''}
                onChange={(e)=>updateRepo(idx, 'collection', e.target.value)}
                placeholder={collection}
                style={{width:'100%',padding:6,fontSize:13}}
              />
            </div>

            <div style={{display:'flex',alignItems:'center',gap:8}}>
              <input
                type="checkbox"
                id={`auto-ingest-${idx}`}
                checked={repo.auto_ingest !== false}
                onChange={(e)=>updateRepo(idx, 'auto_ingest', e.target.checked)}
              />
              <label htmlFor={`auto-ingest-${idx}`} style={{fontSize:13,cursor:'pointer'}}>
                Auto-ingest on webhook push events
              </label>
            </div>
          </div>
        ))}
      </div>

      <div style={{display:'flex',gap:12,alignItems:'center'}}>
        <button onClick={saveConfig} disabled={saving} style={{padding:'8px 24px',fontSize:14,fontWeight:'bold'}}>
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
        <button onClick={fetchConfig} disabled={loading} style={{padding:'8px 16px',fontSize:14}}>
          Reload
        </button>
        {saveStatus && (
          <span style={{fontSize:13,color: saveStatus.startsWith('✓') ? '#2d6a2d' : '#d33'}}>
            {saveStatus}
          </span>
        )}
      </div>

      {config && (
        <details style={{marginTop:16,fontSize:12,opacity:0.7}}>
          <summary style={{cursor:'pointer'}}>View raw config JSON</summary>
          <pre style={{background:'#f5f5f5',padding:8,borderRadius:4,overflow:'auto',maxHeight:200}}>
            {JSON.stringify(config, null, 2)}
          </pre>
        </details>
      )}
    </div>
  )
}
