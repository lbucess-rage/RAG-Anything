import { useState, useCallback } from 'react'
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export function useApi() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const get = useCallback(async (url, params = {}) => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get(url, { params })
      return response.data
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message
      setError(errorMsg)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const post = useCallback(async (url, data = {}, config = {}) => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.post(url, data, config)
      return response.data
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message
      setError(errorMsg)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const upload = useCallback(async (url, formData, onProgress) => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.post(url, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            onProgress(percent)
          }
        },
      })
      return response.data
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message
      setError(errorMsg)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const del = useCallback(async (url) => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.delete(url)
      return response.data
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message
      setError(errorMsg)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { get, post, upload, del, loading, error, setError }
}

export { api }
