import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Bot, Database, Loader2, Mic, MicOff, Send, Sparkles, Trash2, UserRound, Volume2, VolumeX } from 'lucide-react'
import { endpoints, getApiBaseUrl } from '../utils/api'

const starters = [
  'Which tower had the most critical failures?',
  'Summarize warning patterns from recent logs.',
  'What action should the engineer take first?',
]

const INITIAL_MESSAGE = { role: 'assistant', text: 'Ask me about uploaded or live BSNL logs. I will answer using the indexed log context. You can also use your microphone! 🎤' }

export default function Chat() {
  const [question, setQuestion] = useState('')
  const [filter, setFilter] = useState('')
  const [messages, setMessages] = useState([INITIAL_MESSAGE])
  const [isStreaming, setIsStreaming] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [ttsEnabled, setTtsEnabled] = useState(false)
  const messagesEndRef = useRef(null)

  function clearChat() {
    if (isStreaming) return
    setMessages([INITIAL_MESSAGE])
    setQuestion('')
  }

  const { data: ragStats } = useQuery({ queryKey: ['ragStats'], queryFn: () => endpoints.ragStats().then((r) => r.data), refetchInterval: 20000 })

  const status = useMemo(() => ragStats?.status || 'empty', [ragStats])

  // ─── VOICE INPUT (Speech-to-Text) ─────────────────────
  function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Try Chrome.')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = 'en-IN'
    recognition.continuous = false
    recognition.interimResults = true

    recognition.onstart = () => setIsListening(true)
    recognition.onend = () => setIsListening(false)

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(r => r[0].transcript)
        .join('')
      setQuestion(transcript)

      // Auto-send when speech is final
      if (event.results[0].isFinal) {
        setTimeout(() => ask(transcript), 300)
      }
    }

    recognition.onerror = () => setIsListening(false)
    recognition.start()
  }

  // ─── TEXT-TO-SPEECH ───────────────────────────────────
  function speak(text) {
    if (!ttsEnabled || !window.speechSynthesis) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'en-IN'
    utterance.rate = 1.0
    utterance.pitch = 1.0
    window.speechSynthesis.speak(utterance)
  }

  // ─── STREAMING CHAT ───────────────────────────────────
  async function ask(text = question) {
    const cleaned = text.trim()
    if (!cleaned || isStreaming) return

    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', text: cleaned }])
    setQuestion('')
    setIsStreaming(true)

    // Add empty assistant message that we'll fill via streaming
    const assistantIndex = messages.length + 1
    setMessages(prev => [...prev, { role: 'assistant', text: '', streaming: true }])

    try {
      const response = await fetch(getApiBaseUrl() + '/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: cleaned,
          filter_severity: filter || null
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullText = ''
      let contextUsed = 0

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.token) {
              fullText += data.token
              setMessages(prev => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                if (last && last.role === 'assistant') {
                  updated[updated.length - 1] = { ...last, text: fullText }
                }
                return updated
              })
            }
            if (data.done) {
              contextUsed = data.context_used || 0
            }
            if (data.error) {
              fullText += `\n\n⚠️ Error: ${data.error}`
            }
          } catch (e) {
            // skip malformed lines
          }
        }
      }

      // Finalize the message
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last && last.role === 'assistant') {
          updated[updated.length - 1] = { ...last, text: fullText, streaming: false, context: contextUsed }
        }
        return updated
      })

      // Text-to-speech
      if (fullText) speak(fullText)

    } catch (error) {
      // Fallback to non-streaming
      try {
        const response = await endpoints.chat({ question: cleaned, filter_severity: filter || null })
        const answer = response.data.answer
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            role: 'assistant',
            text: answer,
            context: response.data.context_used,
            sources: response.data.sources || []
          }
          return updated
        })
        if (answer) speak(answer)
      } catch (e) {
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', text: '⚠️ Failed to get response. Backend may not be ready.' }
          return updated
        })
      }
    } finally {
      setIsStreaming(false)
    }
  }

  // Auto-scroll
  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  useMemo(() => { setTimeout(scrollToBottom, 100) }, [messages])

  return (
    <div className="page chat-page fade-in">
      <header className="page-header compact-header">
        <span className="eyebrow">RAG assistant</span>
        <h1>AI chat for network logs</h1>
        <p>Ask operational questions and get streaming AI answers grounded in your logs. Supports voice input! 🎤</p>
      </header>

      <section className="chat-layout">
        <div className="panel chat-panel">
          <div className="chat-toolbar">
            <span className="rag-status"><Database size={15} /> {ragStats?.chromadb_chunks || 0} chunks • {status}</span>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                className="ghost-button icon-button"
                onClick={clearChat}
                disabled={isStreaming || messages.length <= 1}
                title="Clear conversation"
                style={{ width: '36px', minHeight: '36px', padding: 0 }}
              >
                <Trash2 size={15} />
              </button>
              <button
                className={`ghost-button icon-button ${ttsEnabled ? 'tts-active' : ''}`}
                onClick={() => setTtsEnabled(!ttsEnabled)}
                title={ttsEnabled ? 'Disable text-to-speech' : 'Enable text-to-speech'}
                style={{ width: '36px', minHeight: '36px', padding: 0 }}
              >
                {ttsEnabled ? <Volume2 size={15} /> : <VolumeX size={15} />}
              </button>
              <select value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Severity filter">
                <option value="">All severities</option>
                <option value="CRITICAL">Critical only</option>
                <option value="WARNING">Warnings only</option>
                <option value="INFO">Info only</option>
              </select>
            </div>
          </div>

          <div className="messages">
            {messages.map((message, index) => (
              <div className={'message ' + message.role} key={index}>
                <div className="avatar">{message.role === 'assistant' ? <Bot size={17} /> : <UserRound size={17} />}</div>
                <div className="bubble">
                  <p>{message.text}{message.streaming ? <span className="cursor-blink">▌</span> : null}</p>
                  {message.context !== undefined ? <small>Context used: {message.context} log chunks</small> : null}
                  {message.sources?.length ? <div className="sources">{message.sources.slice(0, 3).map((source, sourceIndex) => <span key={sourceIndex}>{typeof source === 'string' ? source : JSON.stringify(source)}</span>)}</div> : null}
                </div>
              </div>
            ))}
            {isStreaming && messages[messages.length - 1]?.text === '' && (
              <div className="message assistant">
                <div className="avatar"><Bot size={17} /></div>
                <div className="bubble"><Loader2 className="spin" size={17} /> Thinking with log context...</div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input" style={{ gridTemplateColumns: '1fr 48px 48px' }}>
            <input value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') ask() }} placeholder="Ask about failures, towers, regions... or use the mic 🎤" />
            <button
              className={`ghost-button icon-button ${isListening ? 'mic-active' : ''}`}
              type="button"
              onClick={startListening}
              disabled={isStreaming}
              aria-label="Voice input"
              title="Speak your question"
            >
              {isListening ? <Mic size={18} className="mic-pulse" /> : <MicOff size={18} />}
            </button>
            <button className="primary-button icon-button" type="button" onClick={() => ask()} disabled={isStreaming || !question.trim()} aria-label="Send question"><Send size={18} /></button>
          </div>
        </div>

        <aside className="panel prompt-panel">
          <span className="eyebrow">Quick prompts</span>
          <h2>Try asking</h2>
          <div className="prompt-list">
            {starters.map((starter) => <button type="button" key={starter} onClick={() => ask(starter)}><Sparkles size={15} /> {starter}</button>)}
          </div>
          <div className="detail-block">
            <h3>🎤 Voice Tips</h3>
            <p style={{ color: 'var(--muted)', fontSize: '13px' }}>Click the mic button and speak your question. Works best in Chrome. Enable the speaker icon for AI voice responses.</p>
          </div>
        </aside>
      </section>
    </div>
  )
}
