import { useState, useEffect, useRef } from 'react'
import { useApi } from '@/hooks/useApi'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { ScrollText, RefreshCw, Trash2, Download, Search, Wifi, WifiOff } from 'lucide-react'

const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
const LEVEL_COLORS = {
  DEBUG: 'bg-gray-500',
  INFO: 'bg-blue-500',
  WARNING: 'bg-yellow-500',
  ERROR: 'bg-red-500',
  CRITICAL: 'bg-purple-500',
}

export default function LogViewer() {
  const [logs, setLogs] = useState([])
  const [level, setLevel] = useState('INFO')
  const [search, setSearch] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)
  const [connected, setConnected] = useState(false)
  const [usePolling, setUsePolling] = useState(true)
  const logContainerRef = useRef(null)
  const { get, loading } = useApi()

  // Note: Log API is not yet implemented in the backend
  // This will show a placeholder until the API is available
  useEffect(() => {
    if (!usePolling) return

    const fetchLogs = async () => {
      // Log endpoint not available yet - show placeholder
      setConnected(false)
      setLogs([
        {
          timestamp: new Date().toISOString(),
          level: 'INFO',
          component: 'system',
          message: 'Log viewer ready. Backend log API not yet implemented.',
        }
      ])
    }

    fetchLogs()
  }, [usePolling])

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  const filteredLogs = logs.filter((log) => {
    if (!search) return true
    const searchLower = search.toLowerCase()
    return (
      log.message?.toLowerCase().includes(searchLower) ||
      log.component?.toLowerCase().includes(searchLower)
    )
  })

  const handleClear = () => {
    setLogs([])
  }

  const handleExport = () => {
    const content = filteredLogs
      .map((log) => `[${log.timestamp}] [${log.level}] [${log.component}] ${log.message}`)
      .join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `logs-${new Date().toISOString().split('T')[0]}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ScrollText className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Log Viewer</h1>
        </div>
        <Badge variant={connected ? 'success' : 'destructive'} className="flex items-center gap-1">
          {connected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          {connected ? 'Connected' : 'Disconnected'}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-4">
            <Select value={level} onValueChange={setLevel}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Level" />
              </SelectTrigger>
              <SelectContent>
                {LOG_LEVELS.map((l) => (
                  <SelectItem key={l} value={l}>
                    {l}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search logs..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant={autoScroll ? 'default' : 'outline'}
                size="sm"
                onClick={() => setAutoScroll(!autoScroll)}
              >
                Auto-scroll
              </Button>

              <Button variant="outline" size="sm" onClick={handleClear}>
                <Trash2 className="h-4 w-4 mr-1" />
                Clear
              </Button>

              <Button variant="outline" size="sm" onClick={handleExport}>
                <Download className="h-4 w-4 mr-1" />
                Export
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div
            ref={logContainerRef}
            className="h-[600px] overflow-auto bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm"
          >
            {filteredLogs.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                {loading ? 'Loading logs...' : 'No logs to display'}
              </div>
            ) : (
              filteredLogs.map((log, idx) => (
                <div
                  key={idx}
                  className="flex gap-2 py-1 border-b border-gray-800 hover:bg-gray-800/50"
                >
                  <span className="text-gray-500 w-20 flex-shrink-0">
                    {log.timestamp
                      ? new Date(log.timestamp).toLocaleTimeString()
                      : '-'}
                  </span>
                  <span
                    className={`${LEVEL_COLORS[log.level] || 'bg-gray-500'} text-white px-2 py-0.5 rounded text-xs w-16 text-center flex-shrink-0`}
                  >
                    {log.level}
                  </span>
                  <span className="text-cyan-400 w-24 flex-shrink-0 truncate">
                    [{log.component || 'system'}]
                  </span>
                  <span className="flex-1 break-all">{log.message}</span>
                  {log.request_id && (
                    <span className="text-gray-500 text-xs flex-shrink-0">
                      {log.request_id}
                    </span>
                  )}
                </div>
              ))
            )}
          </div>

          <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Showing {filteredLogs.length} of {logs.length} logs
            </span>
            <span>Level: {level}+</span>
          </div>
        </CardContent>
      </Card>

      {/* Log Level Guide */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Log Levels</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {LOG_LEVELS.map((l) => (
              <div key={l} className="flex items-center gap-2">
                <span className={`${LEVEL_COLORS[l]} text-white px-2 py-1 rounded text-xs`}>
                  {l}
                </span>
                <span className="text-sm text-muted-foreground">
                  {l === 'DEBUG' && 'Detailed debugging info'}
                  {l === 'INFO' && 'General information'}
                  {l === 'WARNING' && 'Warning messages'}
                  {l === 'ERROR' && 'Error events'}
                  {l === 'CRITICAL' && 'Critical failures'}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
