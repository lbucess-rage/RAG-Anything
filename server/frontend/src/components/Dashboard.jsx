import { useHealth } from '@/hooks/useHealth'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { RefreshCw, Server, Database, Brain, Cpu } from 'lucide-react'

const componentIcons = {
  postgresql: Database,
  neo4j: Database,
  llm: Brain,
  vlm: Brain,
  embedding: Cpu,
  redis: Server,
}

function StatusBadge({ status }) {
  const variants = {
    healthy: 'success',
    unhealthy: 'destructive',
    degraded: 'warning',
  }
  return (
    <Badge variant={variants[status] || 'secondary'}>
      {status || 'unknown'}
    </Badge>
  )
}

function formatUptime(seconds) {
  if (!seconds) return '-'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 24) {
    const days = Math.floor(hours / 24)
    return `${days}d ${hours % 24}h`
  }
  return `${hours}h ${minutes}m`
}

export default function Dashboard() {
  const { health, loading, error, refetch } = useHealth()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Button variant="outline" size="sm" onClick={refetch} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">Error: {error}</p>
          </CardContent>
        </Card>
      )}

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Server className="h-5 w-5" />
            System Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-4">
            <span className="text-sm text-muted-foreground">Overall:</span>
            <StatusBadge status={health?.status} />
            <span className="text-sm text-muted-foreground ml-4">Uptime:</span>
            <span className="font-mono text-sm">{formatUptime(health?.uptime_seconds)}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(health?.components || {}).map(([name, comp]) => {
              const Icon = componentIcons[name] || Server
              return (
                <div
                  key={name}
                  className="flex items-center justify-between p-4 bg-muted/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="h-5 w-5 text-muted-foreground" />
                    <span className="font-medium capitalize">{name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={comp.status} />
                    <span className="text-sm text-muted-foreground font-mono">
                      {comp.latency_ms}ms
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Uptime
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatUptime(health?.uptime_seconds)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Response Time (avg)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {health?.metrics?.avg_response_time_ms || '-'}
              <span className="text-sm font-normal text-muted-foreground ml-1">ms</span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Cache Hit Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {health?.metrics?.cache_hit_rate
                ? `${(health.metrics.cache_hit_rate * 100).toFixed(1)}%`
                : '-'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Queries
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{health?.metrics?.total_queries || '-'}</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" asChild>
              <a href="/query">Test Query</a>
            </Button>
            <Button variant="outline" asChild>
              <a href="/documents">Upload Document</a>
            </Button>
            <Button variant="outline" asChild>
              <a href="/logs">View Logs</a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
