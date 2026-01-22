import { useState, useEffect } from 'react'
import { useApi } from '@/hooks/useApi'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Settings as SettingsIcon, Save, RefreshCw, Server, Database, Brain } from 'lucide-react'

export default function Settings() {
  const [config, setConfig] = useState(null)
  const { get, loading, error } = useApi()

  useEffect(() => {
    const fetchConfig = async () => {
      const response = await get('/api/v1/info')
      if (response) {
        // Transform the response to match expected format
        setConfig({
          app_name: response.app_name,
          app_version: response.version,
          debug: response.debug,
          working_dir: response.settings?.working_dir,
          llm_model: response.settings?.llm_model,
          vlm_model: response.settings?.vlm_model,
          embedding_model: response.settings?.embedding_model,
        })
      }
    }
    fetchConfig()
  }, [get])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <SettingsIcon className="h-6 w-6" />
        <h1 className="text-2xl font-bold">Settings</h1>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Server Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Server className="h-5 w-5" />
            Server Information
          </CardTitle>
          <CardDescription>Current server configuration (read-only)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">App Name</label>
              <p className="mt-1">{config?.app_name || 'RAG-Anything API'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Version</label>
              <p className="mt-1">{config?.app_version || '1.0.0'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Environment</label>
              <Badge variant={config?.debug ? 'warning' : 'success'}>
                {config?.debug ? 'Development' : 'Production'}
              </Badge>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Working Directory</label>
              <p className="mt-1 font-mono text-sm">{config?.working_dir || '-'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* LLM Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Brain className="h-5 w-5" />
            LLM Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">LLM Model</label>
              <p className="mt-1 font-mono text-sm">{config?.llm_model || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">LLM Host</label>
              <p className="mt-1 font-mono text-sm">{config?.llm_host || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">VLM Model</label>
              <p className="mt-1 font-mono text-sm">{config?.vlm_model || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">VLM Host</label>
              <p className="mt-1 font-mono text-sm">{config?.vlm_host || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Embedding Model</label>
              <p className="mt-1 font-mono text-sm">{config?.embedding_model || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Embedding Dimension</label>
              <p className="mt-1">{config?.embedding_dim || '-'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Storage Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Database className="h-5 w-5" />
            Storage Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">KV Storage</label>
              <p className="mt-1 font-mono text-sm">{config?.kv_storage || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Vector Storage</label>
              <p className="mt-1 font-mono text-sm">{config?.vector_storage || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Graph Storage</label>
              <p className="mt-1 font-mono text-sm">{config?.graph_storage || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Document Status Storage</label>
              <p className="mt-1 font-mono text-sm">{config?.doc_status_storage || '-'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Processing Options */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Processing Options</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
              <span>Image Processing</span>
              <Badge variant={config?.enable_image_processing ? 'success' : 'secondary'}>
                {config?.enable_image_processing ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
              <span>Table Processing</span>
              <Badge variant={config?.enable_table_processing ? 'success' : 'secondary'}>
                {config?.enable_table_processing ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
              <span>Equation Processing</span>
              <Badge variant={config?.enable_equation_processing ? 'success' : 'secondary'}>
                {config?.enable_equation_processing ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Parser Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Parser Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">Parser</label>
              <p className="mt-1">{config?.parser || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Parse Method</label>
              <p className="mt-1">{config?.parse_method || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">VLM Response Language</label>
              <p className="mt-1">{config?.vlm_response_language || '-'}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
