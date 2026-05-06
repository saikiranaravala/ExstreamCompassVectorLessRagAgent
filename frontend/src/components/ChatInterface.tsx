import React, { useState, useRef, useEffect } from 'react'
import { api, QueryResponse } from '../services/api'
import { CitationsPanel } from './CitationsPanel'
import { ReasoningTrail } from './ReasoningTrail'
import styles from './ChatInterface.module.css'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  response?: QueryResponse
}

const VARIANTS = [
  { id: 'CloudNative', label: 'Cloud Native' },
  { id: 'ServerBased', label: 'Server Based' },
]

interface ChatInterfaceProps {
  variant: string
  onVariantChange: (variant: string) => void
  sessionId?: string
  onSessionChange?: (sessionId: string) => void
}

const MESSAGES_KEY = (variant: string) => `compass_messages_${variant}`

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  variant,
  onVariantChange,
  sessionId,
  onSessionChange,
}) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedMessage, setSelectedMessage] = useState<QueryResponse | null>(
    null
  )
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load persisted messages when variant changes
  useEffect(() => {
    const stored = localStorage.getItem(MESSAGES_KEY(variant))
    if (stored) {
      try {
        const restored: Message[] = JSON.parse(stored).map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        }))
        setMessages(restored)
      } catch {
        setMessages([])
      }
    } else {
      setMessages([])
    }
    setSelectedMessage(null)
  }, [variant])

  const saveMessages = (msgs: Message[]) => {
    localStorage.setItem(MESSAGES_KEY(variant), JSON.stringify(msgs))
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!input.trim()) return

    // Add user message
    const userMessageId = `msg-${Date.now()}`
    const userMessage: Message = {
      id: userMessageId,
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => {
      const next = [...prev, userMessage]
      saveMessages(next)
      return next
    })
    setInput('')
    setLoading(true)

    try {
      const response = await api.submitQuery({
        query: input,
        variant,
        session_id: sessionId,
      })

      // Update session if needed
      if (!sessionId && onSessionChange) {
        onSessionChange(response.session_id)
      }

      // Add assistant message
      const assistantMessageId = `msg-${Date.now()}`
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        response,
      }

      setMessages((prev) => {
        const next = [...prev, assistantMessage]
        saveMessages(next)
        return next
      })
      setSelectedMessage(response)
    } catch (error) {
      console.error('Query failed:', error)
      const errorMessageId = `msg-${Date.now()}`
      const errorMessage: Message = {
        id: errorMessageId,
        role: 'assistant',
        content:
          'Sorry, an error occurred while processing your query. Please try again.',
        timestamp: new Date(),
      }
      setMessages((prev) => {
        const next = [...prev, errorMessage]
        saveMessages(next)
        return next
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.mainContent}>
        <div className={styles.messagesContainer}>
          {messages.length === 0 && (
            <div className={styles.emptyState}>
              <h2>Welcome to Document Assistant</h2>
              <p>Ask questions about <strong>{VARIANTS.find(v => v.id === variant)?.label}</strong> documentation</p>
              <p className={styles.hint}>
                Select a variant below, then type your question
              </p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`${styles.message} ${styles[message.role]}`}
              onClick={() => {
                if (message.response) {
                  setSelectedMessage(message.response)
                }
              }}
            >
              <div className={styles.messageHeader}>
                <span className={styles.role}>
                  {message.role === 'user' ? 'You' : 'Compass'}
                </span>
                <span className={styles.timestamp}>
                  {message.timestamp.toLocaleTimeString()}
                </span>
              </div>
              <div className={styles.messageContent}>{message.content}</div>
              {message.response && (
                <div className={styles.messageFooter}>
                  <span className={styles.toolCalls}>
                    🔧 {message.response.tool_calls} tool calls
                  </span>
                  <span className={styles.processingTime}>
                    ⏱️ {message.response.processing_time.toFixed(2)}s
                  </span>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className={`${styles.message} ${styles.assistant}`}>
              <div className={styles.messageHeader}>
                <span className={styles.role}>Compass</span>
              </div>
              <div className={styles.loadingIndicator}>
                <span className={styles.dot}></span>
                <span className={styles.dot}></span>
                <span className={styles.dot}></span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className={styles.inputArea}>
          <div className={styles.variantToggle}>
            {VARIANTS.map((v) => (
              <button
                key={v.id}
                type="button"
                className={`${styles.variantBtn} ${variant === v.id ? styles.variantBtnActive : ''}`}
                onClick={() => onVariantChange(v.id)}
                disabled={loading}
              >
                {v.label}
              </button>
            ))}
          </div>
          <form onSubmit={handleSubmit} className={styles.inputForm}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask about ${VARIANTS.find(v => v.id === variant)?.label} documentation...`}
              disabled={loading}
              className={styles.input}
            />
            <button type="submit" disabled={loading} className={styles.submitBtn}>
              {loading ? 'Processing...' : 'Send'}
            </button>
          </form>
        </div>
      </div>

      {selectedMessage && (
        <div className={styles.sidePanel}>
          <div className={styles.sidePanelHeader}>
            <h3>Query Details</h3>
            <button
              onClick={() => setSelectedMessage(null)}
              className={styles.closeBtn}
            >
              ✕
            </button>
          </div>
          <CitationsPanel citations={selectedMessage.citations} />
          <ReasoningTrail response={selectedMessage} />
        </div>
      )}
    </div>
  )
}
