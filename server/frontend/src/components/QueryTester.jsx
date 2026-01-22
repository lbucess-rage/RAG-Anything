import { useState, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useApi } from '@/hooks/useApi'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Search, Clock, Database, Zap, Settings, Play, Square, ChevronDown, ChevronUp } from 'lucide-react'

const QUERY_MODES = [
  { value: 'hybrid', label: 'Hybrid', description: 'Combined local + global search' },
  { value: 'local', label: 'Local', description: 'Entity-centric search' },
  { value: 'global', label: 'Global', description: 'Community-based search' },
  { value: 'naive', label: 'Naive', description: 'Simple vector search' },
  { value: 'mix', label: 'Mix', description: 'Knowledge graph + vector' },
]

const RESPONSE_TYPES = [
  { value: '', label: 'Default' },
  { value: 'Multiple Paragraphs', label: 'Multiple Paragraphs' },
  { value: 'Single Paragraph', label: 'Single Paragraph' },
  { value: 'Bullet Points', label: 'Bullet Points' },
]

// Markdown components styling
const markdownComponents = {
  h1: ({ children }) => <h1 className="text-xl font-bold mt-4 mb-2">{children}</h1>,
  h2: ({ children }) => <h2 className="text-lg font-bold mt-3 mb-2">{children}</h2>,
  h3: ({ children }) => <h3 className="text-base font-semibold mt-2 mb-1">{children}</h3>,
  p: ({ children }) => <p className="mb-2 leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
  li: ({ children }) => <li className="ml-2">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  code: ({ inline, children }) =>
    inline ? (
      <code className="bg-muted px-1 py-0.5 rounded text-sm">{children}</code>
    ) : (
      <pre className="bg-muted p-3 rounded-md overflow-x-auto my-2">
        <code className="text-sm">{children}</code>
      </pre>
    ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-primary/50 pl-4 italic my-2">{children}</blockquote>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-2">
      <table className="min-w-full border-collapse border border-border">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-border bg-muted px-3 py-2 text-left font-semibold">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border border-border px-3 py-2">{children}</td>
  ),
  a: ({ href, children }) => (
    <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
}

export default function QueryTester() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('hybrid')
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [streamingText, setStreamingText] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [showOptions, setShowOptions] = useState(false)
  const [showPromptOptions, setShowPromptOptions] = useState(false)

  // Basic options
  const [useStream, setUseStream] = useState(true)
  const [topK, setTopK] = useState(60)
  const [onlyContext, setOnlyContext] = useState(false)
  const [onlyPrompt, setOnlyPrompt] = useState(false)

  // Prompting options
  const [userPrompt, setUserPrompt] = useState('')
  const [responseType, setResponseType] = useState('')
  const [hlKeywords, setHlKeywords] = useState('')
  const [llKeywords, setLlKeywords] = useState('')

  // Search/Token control options
  const [chunkTopK, setChunkTopK] = useState('')
  const [enableRerank, setEnableRerank] = useState('default')
  const [includeReferences, setIncludeReferences] = useState(true)
  const [includeChunkContent, setIncludeChunkContent] = useState(false)

  const { post, loading, error } = useApi()
  const abortControllerRef = useRef(null)

  // Build query parameters
  const buildQueryParams = useCallback(() => {
    const params = {
      query: query.trim(),
      mode,
      top_k: topK,
      stream: useStream,
      include_references: includeReferences,
      include_chunk_content: includeChunkContent,
    }

    if (onlyContext) params.only_need_context = true
    if (onlyPrompt) params.only_need_prompt = true
    if (userPrompt.trim()) params.user_prompt = userPrompt.trim()
    if (responseType) params.response_type = responseType
    if (hlKeywords.trim()) {
      params.hl_keywords = hlKeywords.split(',').map(k => k.trim()).filter(Boolean)
    }
    if (llKeywords.trim()) {
      params.ll_keywords = llKeywords.split(',').map(k => k.trim()).filter(Boolean)
    }
    if (chunkTopK && !isNaN(parseInt(chunkTopK))) {
      params.chunk_top_k = parseInt(chunkTopK)
    }
    if (enableRerank !== 'default') {
      params.enable_rerank = enableRerank === 'on'
    }

    return params
  }, [query, mode, topK, useStream, onlyContext, onlyPrompt, userPrompt, responseType,
      hlKeywords, llKeywords, chunkTopK, enableRerank, includeReferences, includeChunkContent])

  // Streaming query handler
  const handleStreamingQuery = useCallback(async () => {
    if (!query.trim()) return

    setIsStreaming(true)
    setStreamingText('')
    setResult(null)

    const startTime = Date.now()
    abortControllerRef.current = new AbortController()

    try {
      const baseUrl = import.meta.env.VITE_API_URL || ''
      const params = buildQueryParams()

      const response = await fetch(`${baseUrl}/api/v1/query/search/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullText = ''
      let latencyMs = 0

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.chunk) {
                fullText += data.chunk
                setStreamingText(fullText)
              }
              if (data.done) {
                latencyMs = data.latency_ms || (Date.now() - startTime)
              }
              if (data.error) {
                throw new Error(data.error)
              }
            } catch (e) {
              if (e.message !== 'Unexpected end of JSON input') {
                console.error('Parse error:', e)
              }
            }
          }
        }
      }

      const resultData = {
        query: query.trim(),
        answer: fullText,
        mode: mode,
        params: params,
        metadata: {
          response_time_ms: latencyMs || (Date.now() - startTime),
          cache_hit: false,
          streamed: true,
        }
      }

      setResult(resultData)
      setHistory((prev) => [
        {
          query: query.trim(),
          mode,
          response: resultData,
          timestamp: new Date().toISOString(),
        },
        ...prev.slice(0, 9),
      ])

    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Streaming error:', err)
        setResult({
          query: query.trim(),
          answer: `Error: ${err.message}`,
          mode,
          metadata: { response_time_ms: Date.now() - startTime, error: true }
        })
      }
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }, [query, mode, buildQueryParams])

  // Regular (non-streaming) query handler
  const handleRegularQuery = async () => {
    if (!query.trim()) return

    const params = buildQueryParams()
    const response = await post('/api/v1/query/search', params)

    if (response?.success && response?.data) {
      const resultData = {
        query: query.trim(),
        answer: response.data.response || response.data.answer || '',
        mode: mode,
        context: response.data.context,
        prompt: response.data.prompt,
        params: params,
        metadata: {
          response_time_ms: response.data.latency_ms || 0,
          cache_hit: response.data.cached || false,
          streamed: false,
        }
      }
      setResult(resultData)
      setHistory((prev) => [
        {
          query: query.trim(),
          mode,
          response: resultData,
          timestamp: new Date().toISOString(),
        },
        ...prev.slice(0, 9),
      ])
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    if (useStream) {
      await handleStreamingQuery()
    } else {
      await handleRegularQuery()
    }
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }

  const handleHistoryClick = (item) => {
    setQuery(item.query)
    setMode(item.mode)
    setResult(item.response)
    setStreamingText('')
  }

  const displayAnswer = isStreaming ? streamingText : (result?.answer || '')

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Search className="h-6 w-6" />
        <h1 className="text-2xl font-bold">Query Tester</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Query Input */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Query Input</CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowOptions(!showOptions)}
                  >
                    <Settings className="h-4 w-4 mr-1" />
                    Options
                    {showOptions ? <ChevronUp className="h-3 w-3 ml-1" /> : <ChevronDown className="h-3 w-3 ml-1" />}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <Textarea
                  placeholder="Enter your question here..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  rows={4}
                  className="resize-none"
                />

                {/* Basic Options */}
                {showOptions && (
                  <div className="space-y-4">
                    {/* Search Options */}
                    <div className="p-4 bg-muted/50 rounded-lg space-y-4">
                      <h4 className="font-medium text-sm">Search Options</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <label className="text-xs text-muted-foreground block mb-1">
                            Streaming
                          </label>
                          <Select value={useStream ? 'on' : 'off'} onValueChange={(v) => setUseStream(v === 'on')}>
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="on">On</SelectItem>
                              <SelectItem value="off">Off</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <label className="text-xs text-muted-foreground block mb-1">
                            Top K (1-200)
                          </label>
                          <Input
                            type="number"
                            min={1}
                            max={200}
                            value={topK}
                            onChange={(e) => setTopK(Number(e.target.value))}
                            className="h-8"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-muted-foreground block mb-1">
                            Chunk Top K
                          </label>
                          <Input
                            type="number"
                            min={1}
                            max={500}
                            value={chunkTopK}
                            onChange={(e) => setChunkTopK(e.target.value)}
                            placeholder="Default"
                            className="h-8"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-muted-foreground block mb-1">
                            Rerank
                          </label>
                          <Select value={enableRerank} onValueChange={setEnableRerank}>
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="default">Default</SelectItem>
                              <SelectItem value="on">On</SelectItem>
                              <SelectItem value="off">Off</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <label className="text-xs text-muted-foreground block mb-1">
                            Only Context
                          </label>
                          <Select value={onlyContext ? 'on' : 'off'} onValueChange={(v) => setOnlyContext(v === 'on')}>
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="off">Off</SelectItem>
                              <SelectItem value="on">On</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <label className="text-xs text-muted-foreground block mb-1">
                            Only Prompt
                          </label>
                          <Select value={onlyPrompt ? 'on' : 'off'} onValueChange={(v) => setOnlyPrompt(v === 'on')}>
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="off">Off</SelectItem>
                              <SelectItem value="on">On</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <label className="text-xs text-muted-foreground block mb-1">
                            Include References
                          </label>
                          <Select value={includeReferences ? 'on' : 'off'} onValueChange={(v) => setIncludeReferences(v === 'on')}>
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="on">On</SelectItem>
                              <SelectItem value="off">Off</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <label className="text-xs text-muted-foreground block mb-1">
                            Include Chunks
                          </label>
                          <Select value={includeChunkContent ? 'on' : 'off'} onValueChange={(v) => setIncludeChunkContent(v === 'on')}>
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="off">Off</SelectItem>
                              <SelectItem value="on">On</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </div>

                    {/* Prompting Options */}
                    <div className="p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg space-y-4">
                      <div
                        className="flex items-center justify-between cursor-pointer"
                        onClick={() => setShowPromptOptions(!showPromptOptions)}
                      >
                        <h4 className="font-medium text-sm">Prompting Options</h4>
                        {showPromptOptions ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </div>

                      {showPromptOptions && (
                        <div className="space-y-4">
                          <div>
                            <label className="text-xs text-muted-foreground block mb-1">
                              Response Type
                            </label>
                            <Select value={responseType} onValueChange={setResponseType}>
                              <SelectTrigger className="h-8">
                                <SelectValue placeholder="Default" />
                              </SelectTrigger>
                              <SelectContent>
                                {RESPONSE_TYPES.map((t) => (
                                  <SelectItem key={t.value} value={t.value}>
                                    {t.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                              <label className="text-xs text-muted-foreground block mb-1">
                                High-Level Keywords (comma separated)
                              </label>
                              <Input
                                value={hlKeywords}
                                onChange={(e) => setHlKeywords(e.target.value)}
                                placeholder="e.g., 충전기, 고장, LCD"
                                className="h-8"
                              />
                            </div>
                            <div>
                              <label className="text-xs text-muted-foreground block mb-1">
                                Low-Level Keywords (comma separated)
                              </label>
                              <Input
                                value={llKeywords}
                                onChange={(e) => setLlKeywords(e.target.value)}
                                placeholder="e.g., 해피차저, E-pit"
                                className="h-8"
                              />
                            </div>
                          </div>
                          <div>
                            <label className="text-xs text-muted-foreground block mb-1">
                              Custom User Prompt (overrides default template)
                            </label>
                            <Textarea
                              value={userPrompt}
                              onChange={(e) => setUserPrompt(e.target.value)}
                              placeholder="Enter custom prompt to override the default template..."
                              rows={3}
                              className="resize-none text-sm"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <label className="text-sm font-medium text-muted-foreground mb-2 block">
                      Search Mode
                    </label>
                    <Select value={mode} onValueChange={setMode}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select mode" />
                      </SelectTrigger>
                      <SelectContent>
                        {QUERY_MODES.map((m) => (
                          <SelectItem key={m.value} value={m.value}>
                            <div>
                              <span className="font-medium">{m.label}</span>
                              <span className="text-muted-foreground ml-2 text-xs">
                                - {m.description}
                              </span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {isStreaming ? (
                    <Button
                      type="button"
                      variant="destructive"
                      onClick={handleStop}
                      className="mt-6"
                    >
                      <Square className="h-4 w-4 mr-2" />
                      Stop
                    </Button>
                  ) : (
                    <Button
                      type="submit"
                      disabled={loading || !query.trim()}
                      className="mt-6"
                    >
                      {loading ? (
                        <>
                          <span className="animate-spin mr-2">...</span>
                          Processing
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4 mr-2" />
                          {useStream ? 'Stream' : 'Search'}
                        </>
                      )}
                    </Button>
                  )}
                </div>

                {error && (
                  <div className="p-3 bg-destructive/10 text-destructive rounded-md text-sm">
                    {error}
                  </div>
                )}
              </form>
            </CardContent>
          </Card>

          {/* Result */}
          {(result || isStreaming) && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg flex items-center gap-2">
                    Response
                    {isStreaming && (
                      <Badge variant="secondary" className="animate-pulse">
                        Streaming...
                      </Badge>
                    )}
                  </CardTitle>
                  {result?.metadata && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Badge variant="outline">{result.mode}</Badge>
                      {result.metadata.streamed && (
                        <Badge variant="secondary">Streamed</Badge>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {Math.round(result.metadata.response_time_ms)}ms
                      </span>
                      <span className="flex items-center gap-1">
                        <Database className="h-3 w-3" />
                        {result.metadata.cache_hit ? 'Cache Hit' : 'Cache Miss'}
                      </span>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="answer">
                  <TabsList>
                    <TabsTrigger value="answer">Answer</TabsTrigger>
                    {result?.context && <TabsTrigger value="context">Context</TabsTrigger>}
                    {result?.prompt && <TabsTrigger value="prompt">Prompt</TabsTrigger>}
                    <TabsTrigger value="params">Parameters</TabsTrigger>
                    <TabsTrigger value="raw">Raw JSON</TabsTrigger>
                  </TabsList>
                  <TabsContent value="answer" className="mt-4">
                    <div className="p-4 bg-muted/50 rounded-lg prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={markdownComponents}
                      >
                        {displayAnswer || '*Waiting for response...*'}
                      </ReactMarkdown>
                    </div>
                  </TabsContent>
                  {result?.context && (
                    <TabsContent value="context" className="mt-4">
                      <pre className="p-4 bg-muted/50 rounded-lg overflow-auto text-xs whitespace-pre-wrap max-h-96">
                        {result.context}
                      </pre>
                    </TabsContent>
                  )}
                  {result?.prompt && (
                    <TabsContent value="prompt" className="mt-4">
                      <pre className="p-4 bg-muted/50 rounded-lg overflow-auto text-xs whitespace-pre-wrap max-h-96">
                        {result.prompt}
                      </pre>
                    </TabsContent>
                  )}
                  <TabsContent value="params" className="mt-4">
                    <pre className="p-4 bg-muted/50 rounded-lg overflow-auto text-xs">
                      {JSON.stringify(result?.params || buildQueryParams(), null, 2)}
                    </pre>
                  </TabsContent>
                  <TabsContent value="raw" className="mt-4">
                    <pre className="p-4 bg-muted/50 rounded-lg overflow-auto text-xs max-h-96">
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1 space-y-4">
          {/* History */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Recent Queries
              </CardTitle>
            </CardHeader>
            <CardContent>
              {history.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No queries yet
                </p>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {history.map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleHistoryClick(item)}
                      className="w-full text-left p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                    >
                      <p className="text-sm font-medium truncate">{item.query}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {item.mode}
                        </Badge>
                        {item.response?.metadata?.streamed && (
                          <Badge variant="secondary" className="text-xs">
                            Streamed
                          </Badge>
                        )}
                        <span className="text-xs text-muted-foreground">
                          {new Date(item.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Mode Guide */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Search Modes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                {QUERY_MODES.map((m) => (
                  <div key={m.value}>
                    <span className="font-medium">{m.label}</span>
                    <p className="text-muted-foreground">{m.description}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Prompting Guide */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Prompting Guide</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="font-medium">Response Type</span>
                  <p className="text-muted-foreground">Format of the answer output</p>
                </div>
                <div>
                  <span className="font-medium">HL Keywords</span>
                  <p className="text-muted-foreground">High-level topics to prioritize</p>
                </div>
                <div>
                  <span className="font-medium">LL Keywords</span>
                  <p className="text-muted-foreground">Specific terms to focus on</p>
                </div>
                <div>
                  <span className="font-medium">User Prompt</span>
                  <p className="text-muted-foreground">Custom prompt template override</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
