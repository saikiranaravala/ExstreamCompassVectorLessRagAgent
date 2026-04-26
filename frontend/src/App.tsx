import React, { useState, useEffect } from 'react'
import { api } from './services/api'
import { VariantSelector } from './components/VariantSelector'
import { ChatInterface } from './components/ChatInterface'
import styles from './App.module.css'

const App: React.FC = () => {
  const [variant, setVariant] = useState<string>('CloudNative')
  const [sessionId, setSessionId] = useState<string | undefined>(undefined)
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Check if user is authenticated
    const token = localStorage.getItem('access_token')

    if (token) {
      loadUserProfile()
    } else {
      setLoading(false)
    }
  }, [])

  const loadUserProfile = async () => {
    try {
      const profile = await api.getUserProfile()
      setUser(profile)
      setVariant(profile.variant || 'CloudNative')
    } catch (err) {
      console.error('Failed to load user profile:', err)
      // User might be logged out
      localStorage.removeItem('access_token')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = async (email: string, password: string) => {
    try {
      setError(null)
      const token = await api.login(email, password)
      localStorage.setItem('access_token', token)
      await loadUserProfile()
    } catch (err) {
      setError('Login failed. Please check your credentials.')
      console.error('Login error:', err)
    }
  }

  const handleLogout = async () => {
    try {
      await api.logout()
      setUser(null)
      setSessionId(undefined)
      localStorage.removeItem('access_token')
    } catch (err) {
      console.error('Logout error:', err)
    }
  }

  const handleVariantChange = (newVariant: string) => {
    setVariant(newVariant)
    // Reset session when variant changes
    setSessionId(undefined)
  }

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingScreen}>
          <div className={styles.spinner}></div>
          <p>Loading...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className={styles.container}>
        <LoginForm onLogin={handleLogin} error={error} />
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.logo}>
            <h1>Compass RAG</h1>
            <p className={styles.subtitle}>Documentation Assistant</p>
          </div>
          <div className={styles.userSection}>
            <span className={styles.userEmail}>{user.email}</span>
            <button
              onClick={handleLogout}
              className={styles.logoutBtn}
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className={styles.content}>
        <VariantSelector
          selectedVariant={variant}
          onVariantChange={handleVariantChange}
        />
        <ChatInterface
          variant={variant}
          sessionId={sessionId}
          onSessionChange={setSessionId}
        />
      </div>
    </div>
  )
}

interface LoginFormProps {
  onLogin: (email: string, password: string) => void
  error: string | null
}

const LoginForm: React.FC<LoginFormProps> = ({ onLogin, error }) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onLogin(email, password)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.loginContainer}>
      <div className={styles.loginBox}>
        <h2>Compass RAG</h2>
        <p className={styles.loginSubtitle}>Documentation Assistant</p>

        {error && <div className={styles.errorMessage}>{error}</div>}

        <form onSubmit={handleSubmit} className={styles.loginForm}>
          <div className={styles.formGroup}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              required
              disabled={loading}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={styles.loginButton}
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <p className={styles.loginHint}>
          Use any email and password for testing
        </p>
      </div>
    </div>
  )
}

export default App
