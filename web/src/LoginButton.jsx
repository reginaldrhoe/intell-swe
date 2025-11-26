import React from 'react'

export default function LoginButton(){
  const startOauth = (provider='github') => {
    const url = `/auth/login?provider=${provider}`
    window.location.href = url
  }

  return (
    <div>
      <button onClick={() => startOauth('github')}>Login with GitHub</button>
      <button onClick={() => startOauth('gitlab')} style={{marginLeft:8}}>Login with GitLab</button>
    </div>
  )
}
