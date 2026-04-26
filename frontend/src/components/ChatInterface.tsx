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

interface ChatInterfaceProps {
  variant: string
  sessionId?: string
  onSessionChange?: (sessionId: string) => void
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  variant,
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

    setMessages((prev) => [...prev, userMessage])
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

      setMessages((prev) => [...prev, assistantMessage])
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
      setMessages((prev) => [...prev, errorMessage])
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
              <h2>Welcome to Compass RAG</h2>
              <p>Ask questions about {variant} documentation</p>
              <p className={styles.hint}>
                Type your question below to get started
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

        <form onSubmit={handleSubmit} className={styles.inputForm}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about the documentation..."
            disabled={loading}
            className={styles.input}
          />
          <button type="submit" disabled={loading} className={styles.submitBtn}>
            {loading ? 'Processing...' : 'Send'}
          </button>
        </form>
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
