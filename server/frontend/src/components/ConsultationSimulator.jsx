import { useState } from 'react'
import { useApi } from '@/hooks/useApi'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { MessageSquare, Send, Clock, User, Bot, FileText, History } from 'lucide-react'

const CUSTOMER_TYPES = ['일반', 'VIP', '신규', '기업']
const SERVICE_TYPES = ['전기차 충전기', '해피차저', '충전요금', '고장신고', '기타']
const URGENCY_LEVELS = [
  { value: 'low', label: '낮음' },
  { value: 'normal', label: '보통' },
  { value: 'high', label: '긴급' },
]

export default function ConsultationSimulator() {
  const [query, setQuery] = useState('')
  const [customerType, setCustomerType] = useState('일반')
  const [serviceType, setServiceType] = useState('')
  const [urgency, setUrgency] = useState('normal')
  const [includeScript, setIncludeScript] = useState(true)
  const [includeReferences, setIncludeReferences] = useState(true)
  const [result, setResult] = useState(null)
  const [chatHistory, setChatHistory] = useState([])
  const { post, loading, error } = useApi()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    const previousQueries = chatHistory
      .filter((m) => m.role === 'user')
      .map((m) => m.content)
      .slice(-3)

    const response = await post('/api/v1/query/consultation', {
      query: query.trim(),
      mode: 'hybrid',
      session_id: null, // For conversation continuity
    })

    if (response?.success && response?.data) {
      const resultData = {
        answer: response.data.response || response.data.answer || '',
        metadata: {
          query_id: response.request_id,
          response_time_ms: response.data.response_time_ms || 0,
          mode: 'hybrid',
          confidence: 0.85,
          cache_hit: response.data.cache_hit || false,
        }
      }
      setResult(resultData)
      setChatHistory((prev) => [
        ...prev,
        { role: 'user', content: query.trim(), timestamp: new Date().toISOString() },
        { role: 'assistant', content: resultData.answer, timestamp: new Date().toISOString(), metadata: resultData.metadata },
      ])
      setQuery('')
    }
  }

  const handleClearChat = () => {
    setChatHistory([])
    setResult(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <MessageSquare className="h-6 w-6" />
        <h1 className="text-2xl font-bold">Consultation Simulator</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat Area */}
        <div className="lg:col-span-2 space-y-4">
          {/* Context Settings */}
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-sm font-medium">Context Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Customer Type</label>
                  <Select value={customerType} onValueChange={setCustomerType}>
                    <SelectTrigger className="w-28">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CUSTOMER_TYPES.map((t) => (
                        <SelectItem key={t} value={t}>{t}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Service Type</label>
                  <Select value={serviceType} onValueChange={setServiceType}>
                    <SelectTrigger className="w-36">
                      <SelectValue placeholder="Select..." />
                    </SelectTrigger>
                    <SelectContent>
                      {SERVICE_TYPES.map((t) => (
                        <SelectItem key={t} value={t}>{t}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Urgency</label>
                  <Select value={urgency} onValueChange={setUrgency}>
                    <SelectTrigger className="w-24">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {URGENCY_LEVELS.map((l) => (
                        <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Chat History */}
          <Card className="min-h-[400px] flex flex-col">
            <CardHeader className="py-3 flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <History className="h-4 w-4" />
                Chat History
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={handleClearChat}>
                Clear
              </Button>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto">
              {chatHistory.length === 0 ? (
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  <p>Start a conversation by typing a question below</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {chatHistory.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}
                    >
                      {msg.role === 'assistant' && (
                        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                          <Bot className="h-4 w-4 text-primary-foreground" />
                        </div>
                      )}
                      <div
                        className={`max-w-[80%] p-3 rounded-lg ${
                          msg.role === 'user'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted'
                        }`}
                      >
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        {msg.metadata && (
                          <div className="mt-2 flex gap-2 text-xs opacity-70">
                            <span>{msg.metadata.response_time_ms}ms</span>
                            <span>{msg.metadata.mode}</span>
                          </div>
                        )}
                      </div>
                      {msg.role === 'user' && (
                        <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                          <User className="h-4 w-4" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Input */}
          <Card>
            <CardContent className="pt-4">
              <form onSubmit={handleSubmit} className="flex gap-3">
                <Textarea
                  placeholder="Enter customer question..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  rows={2}
                  className="flex-1 resize-none"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSubmit(e)
                    }
                  }}
                />
                <Button type="submit" disabled={loading || !query.trim()}>
                  {loading ? (
                    <span className="animate-spin">...</span>
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </form>
              {error && (
                <p className="mt-2 text-sm text-destructive">{error}</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Response Details */}
        <div className="space-y-4">
          {result && (
            <>
              {/* Script */}
              {result.script && (
                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-sm font-medium">Consultation Script</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Greeting</p>
                      <p className="p-2 bg-muted rounded">{result.script.greeting}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Main Response</p>
                      <p className="p-2 bg-muted rounded whitespace-pre-wrap">
                        {result.script.main_response}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Closing</p>
                      <p className="p-2 bg-muted rounded">{result.script.closing}</p>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* References */}
              {result.references?.length > 0 && (
                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      References
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {result.references.map((ref, idx) => (
                        <div key={idx} className="p-2 bg-muted rounded text-sm">
                          <p className="font-medium">{ref.title}</p>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                            {ref.excerpt}
                          </p>
                          <Badge variant="outline" className="mt-1 text-xs">
                            Score: {(ref.relevance_score * 100).toFixed(0)}%
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Metadata */}
              <Card>
                <CardHeader className="py-3">
                  <CardTitle className="text-sm font-medium">Response Metadata</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Query ID</span>
                      <span className="font-mono">{result.metadata?.query_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Response Time</span>
                      <span>{result.metadata?.response_time_ms}ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Mode</span>
                      <Badge variant="outline">{result.metadata?.mode}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Confidence</span>
                      <span>{((result.metadata?.confidence || 0) * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Cache Hit</span>
                      <span>{result.metadata?.cache_hit ? 'Yes' : 'No'}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          {!result && (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Response details will appear here</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
