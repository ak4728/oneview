import React, { useEffect, useState } from 'react'

export default function App() {
  const [message, setMessage] = useState<string>('Loading...')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((data) => setMessage(data.status || 'ok'))
      .catch(() => setMessage('API unavailable'))
  }, [])

  return (
    <div className="app">
      <h1>OneView (React + Vite)</h1>
      <p>API status: {message}</p>
    </div>
  )
}
