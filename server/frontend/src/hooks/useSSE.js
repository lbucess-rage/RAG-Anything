import { useState, useEffect, useRef, useCallback } from 'react'

export function useSSE(url, maxLogs = 500) {
  const [logs, setLogs] = useState([])
  const [connected, setConnected] = useState(false)
  const eventSourceRef = useRef(null)

  useEffect(() => {
    if (!url) return

    const baseUrl = import.meta.env.VITE_API_URL || ''
    const fullUrl = `${baseUrl}${url}`

    const eventSource = new EventSource(fullUrl)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setConnected(true)
    }

    eventSource.addEventListener('log', (event) => {
      try {
        const logEntry = JSON.parse(event.data)
        setLogs((prev) => {
          const newLogs = [...prev, logEntry]
          if (newLogs.length > maxLogs) {
            return newLogs.slice(-maxLogs)
          }
          return newLogs
        })
      } catch (err) {
        console.error('Failed to parse log entry:', err)
      }
    })

    eventSource.onerror = () => {
      setConnected(false)
    }

    return () => {
      eventSource.close()
      setConnected(false)
    }
  }, [url, maxLogs])

  const clearLogs = useCallback(() => setLogs([]), [])

  return { logs, connected, clearLogs }
}
