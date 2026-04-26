# Compass RAG Frontend

React + TypeScript web UI for the Compass RAG agent.

## Features

- **Variant Selector** — Choose between Cloud Native or Server-Based documentation
- **Chat Interface** — Interactive conversation with the RAG agent
- **Citations Panel** — View sources for each answer with document paths and content
- **Reasoning Trail** — See tool calls, processing time, and query metadata
- **Session Management** — Persistent conversation sessions
- **Authentication** — Token-based login with rate limiting

## Setup

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
cd frontend
npm install
```

### Development

Start the development server (runs on http://localhost:3000):

```bash
npm run dev
```

The server proxies `/api/*` requests to `http://localhost:8000` (backend).

### Build

```bash
npm run build
```

Output is in `dist/`.

## Project Structure

```
src/
├── main.tsx           # React entry point
├── index.css          # Global styles
├── App.tsx            # Main app component with auth
├── App.module.css     # App styles
├── services/
│   └── api.ts         # API client with axios
└── components/
    ├── VariantSelector.tsx        # Variant selection UI
    ├── ChatInterface.tsx           # Main chat component
    ├── CitationsPanel.tsx          # Citations display
    └── ReasoningTrail.tsx          # Query metadata and tool calls
```

## API Integration

The frontend communicates with the backend API at `/api/v1`:

- **POST /query** — Submit a query
- **GET /session/{id}** — Get session info
- **DELETE /session/{id}** — Close session
- **GET /user/profile** — Get current user
- **POST /login** — User login
- **POST /logout** — User logout

See `src/services/api.ts` for full client implementation.

## Environment

Create `.env.local` for development overrides:

```
VITE_API_URL=http://localhost:8000/api/v1
```

## Types

All API responses are fully typed in `src/services/api.ts`:

- `QueryRequest` / `QueryResponse`
- `Citation` / `SessionInfo`
- `UserProfile` / `RateLimitInfo`

## Styling

CSS Modules are used for component scoping. Global variables in `index.css`:

- `--primary` / `--primary-dark`
- `--gray-*` (gray palette)
- `--success` / `--danger` / `--warning`

Dark mode is supported via `prefers-color-scheme` media query.

## Browser Support

Modern browsers with ES2020 support (Chrome, Firefox, Safari, Edge).
