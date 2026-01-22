import { useState, useEffect, useCallback } from 'react'
import { useApi } from './useApi'

export function useHealth(interval = 30000) {
  const { get } = useApi()
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchHealth = useCallback(async () => {
    setLoading(true)
    try {
      const response = await get('/api/v1/health')
      if (response?.success && response?.data) {
        // Transform backend response to match frontend expected format
        const data = response.data
        const componentsMap = {}
        if (data.components) {
          data.components.forEach(comp => {
            componentsMap[comp.name] = {
              status: comp.status,
              latency_ms: comp.latency_ms || 0,
              message: comp.message,
              details: comp.details
            }
          })
        }
        setHealth({
          status: data.status,
          uptime_seconds: data.uptime_seconds,
          components: componentsMap,
          metrics: data.metrics || {}
        })
        setError(null)
      } else {
        setError('Failed to fetch health status')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [get])

  useEffect(() => {
    fetchHealth()

    if (interval > 0) {
      const timer = setInterval(fetchHealth, interval)
      return () => clearInterval(timer)
    }
  }, [fetchHealth, interval])

  return { health, loading, error, refetch: fetchHealth }
}
