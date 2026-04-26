import axios, { AxiosInstance, AxiosError } from 'axios'

export interface QueryRequest {
  query: string
  variant?: string
  session_id?: string
}

export interface Citation {
  doc_id: string
  title: string
  path: string
  content: string
}

export interface QueryResponse {
  session_id: string
  answer: string
  citations: Citation[]
  tool_calls: number
  processing_time: number
  variant: string
}

export interface SessionInfo {
  session_id: string
  created_at: string
  last_activity: string
  variant: string
  statistics: SessionStats
}

export interface SessionStats {
  total_queries: number
  total_tool_calls: number
  total_file_reads: number
  average_response_time: number
}

export interface UserProfile {
  user_id: string
  email: string
  roles: string[]
  variant: string
}

export interface RateLimitInfo {
  user_id: string
  remaining_per_minute: number
  remaining_per_hour: number
}

class CompassAPI {
  private client: AxiosInstance

  constructor(baseURL: string = '/api/v1') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add token to requests if available
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    // Handle token expiry
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // Authentication
  async login(email: string, password: string): Promise<string> {
    const response = await this.client.post<{ access_token: string }>(
      '/login',
      { email, password }
    )
    return response.data.access_token
  }

  async logout(): Promise<void> {
    await this.client.post('/logout')
    localStorage.removeItem('access_token')
  }

  async getUserProfile(): Promise<UserProfile> {
    const response = await this.client.get<UserProfile>('/user/profile')
    return response.data
  }

  // Queries
  async submitQuery(request: QueryRequest): Promise<QueryResponse> {
    const params = new URLSearchParams({
      query: request.query,
      ...(request.variant && { variant: request.variant }),
      ...(request.session_id && { session_id: request.session_id }),
    })

    const response = await this.client.post<QueryResponse>(
      `/query?${params}`
    )
    return response.data
  }

  // Sessions
  async getSession(sessionId: string): Promise<SessionInfo> {
    const response = await this.client.get<SessionInfo>(
      `/session/${sessionId}`
    )
    return response.data
  }

  async closeSession(sessionId: string): Promise<void> {
    await this.client.delete(`/session/${sessionId}`)
  }

  async getSessionQueries(sessionId: string): Promise<any[]> {
    const response = await this.client.get<{ queries: any[] }>(
      `/session/${sessionId}/queries`
    )
    return response.data.queries
  }

  // Rate limiting
  async getRateLimit(): Promise<RateLimitInfo> {
    const response = await this.client.get<RateLimitInfo>(
      '/user/rate-limit'
    )
    return response.data
  }

  // Health
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get<{ status: string }>('/health')
    return response.data
  }
}

export const api = new CompassAPI()
