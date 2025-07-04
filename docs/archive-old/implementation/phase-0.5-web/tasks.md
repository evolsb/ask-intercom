# Phase 0.5 Web Deployment Tasks

> **Transform CLI into shareable web app** - prioritized by risk and dependencies

## Core Infrastructure (De-risk first)

### Project Setup
- [ ] Create `feature/web-deployment` branch
- [ ] Create `frontend/` directory structure
- [ ] Initialize React + TypeScript app with Vite using pnpm
- [ ] Verify frontend development server works
- [ ] Set up basic FastAPI app structure
- [ ] Create Docker configuration files
- [ ] Add web dependencies to `pyproject.toml`

### Backend Architecture
- [x] Integrate existing CLI logic into FastAPI
- [x] Implement async request handling
- [x] Create secure API key handling with localStorage support
- [ ] **PRIORITY: Enhanced Session Management & Logging**
  - [ ] Implement session IDs for request correlation
  - [ ] Add structured JSON logging with timestamps
  - [ ] Create real-time log tailing for Claude debugging
  - [ ] Build local session storage with full context
  - [ ] Add environment validation & health checks
  - [ ] Implement detailed frontend error display
- [ ] Build comprehensive logging system (30-day retention)

### Real-Time Updates (SSE)
- [ ] Implement Server-Sent Events endpoint
- [ ] Create progress streaming for long-running queries
- [ ] Handle connection drops and reconnection
- [ ] Test with 20-30 second query times

## API Development

### FastAPI Endpoints
- [x] Create API endpoints wrapping CLI logic
- [x] Implement request/response models
- [x] Add input validation and sanitization
- [ ] **PRIORITY: Enhanced Health & Diagnostics**
  - [ ] Create `/api/debug` endpoint with system status
  - [ ] Add API connectivity tests (Intercom/OpenAI)
  - [ ] Implement environment variable validation
  - [ ] Add error categorization and tracking
- [x] Create health check and status endpoints
- [ ] Set up basic rate limiting

### Authentication & Security
- [ ] Implement dual-mode authentication (env vars for Docker, localStorage for SaaS)
- [ ] Create API key validation middleware
- [ ] Set up CORS configuration
- [ ] Implement request logging for learning

## Frontend Development

### React + Vite Setup
- [ ] Configure Vite build pipeline
- [ ] Set up TypeScript configuration
- [ ] Install and configure Tailwind CSS + shadcn/ui (minimal macOS/iOS aesthetic)
- [ ] Set up Zustand for state management
- [ ] Configure development proxy to backend

### Core Components
- [x] Build API key setup component (localStorage)
- [x] Create query input form component
- [ ] Implement SSE progress display component
- [x] Create analysis results display component
- [ ] **PRIORITY: Enhanced Error Handling**
  - [ ] Add detailed error messages in UI
  - [ ] Implement retry mechanisms for transient failures
  - [ ] Create error categorization display
  - [ ] Add session correlation for debugging
- [x] Add error boundary and fallback UI

### User Experience
- [ ] Design responsive layout
- [ ] Implement loading states with SSE progress
- [ ] Add error handling and user feedback
- [ ] Create mobile-friendly interface
- [ ] Add privacy disclaimer (30-day data retention)

## Critical Debugging & Logging Infrastructure

### Session Management & Correlation
- [ ] Generate unique session IDs for each user interaction
- [ ] Create request correlation IDs for tracing queries
- [ ] Implement session persistence across browser refreshes
- [ ] Build session history storage with full context

### Structured Logging System
- [ ] Implement JSON logging with timestamps and session IDs
- [ ] Create separate log files for frontend/backend with correlation
- [ ] Add real-time log tailing for Claude debugging
- [ ] Include error stack traces with full context
- [ ] Log performance metrics (response times, token usage, costs)

### Claude Integration Tools
- [ ] Create log analysis commands for Claude
- [ ] Implement session replay functionality
- [ ] Add error pattern detection
- [ ] Build performance trend analysis

### Environment Validation & Health Checks
- [ ] Validate .env file and API key formats on startup
- [ ] Test Intercom/OpenAI connectivity before accepting requests
- [ ] Create `/api/debug` endpoint with system diagnostics
- [ ] Add clear error messages for configuration issues

### Local Analytics Storage
```
.ask-intercom-analytics/
├── sessions/           # Full session history for learning
├── errors/            # Categorized error tracking
├── performance/       # Response time trends
└── insights/          # Quality control analysis
```

### Frontend Error Enhancement
- [ ] Display detailed error messages instead of generic failures
- [ ] Add retry mechanisms for API failures
- [ ] Show session IDs for user support
- [ ] Implement error categorization in UI

## Advanced Features

### Data & Analytics
- [ ] Implement comprehensive request/response logging
- [ ] Create 30-day auto-deletion for logs
- [ ] Build usage analytics dashboard
- [ ] Track query patterns and insights

### Export & Sharing
- [ ] Implement query sharing functionality
- [ ] Build export capabilities (CSV, JSON)
- [ ] Create persistent query history
- [ ] Add result caching in browser

## Deployment & Operations

### Docker Configuration
- [ ] Create multi-stage Dockerfile
- [ ] Set up docker-compose for local development
- [ ] Configure environment variables
- [ ] Test one-command deployment

### Production Deployment
- [ ] Choose and configure hosting platform (Railway/Vercel)
- [ ] Set up SSL certificates
- [ ] Configure CDN for static assets
- [ ] Implement monitoring and alerts

### Testing & Quality
- [ ] Write API integration tests
- [ ] Create frontend component tests
- [ ] Set up end-to-end testing
- [ ] Add performance benchmarks
- [ ] Test with real 20-30s queries

### Documentation
- [ ] Create API documentation
- [ ] Write deployment guide
- [ ] Document authentication flows
- [ ] Create user onboarding flow

---

## Implementation Phases

### Phase 1: MVP Foundation (Weeks 1-2)
**Goal**: Working web app with core functionality
- FastAPI backend with SSE support
- React + Vite frontend with localStorage auth
- Docker deployment ready
- Basic query → results flow working

### Phase 2: Production Ready (Weeks 3-4)  
**Goal**: Hosted SaaS with full features
- Cloud deployment live
- Comprehensive logging implemented
- Export and sharing features
- Performance optimized for 20-30s queries

### Phase 3: Growth Features (Weeks 5-6)
**Goal**: Enhanced user experience
- Advanced analytics dashboard
- Team collaboration features
- A/B testing infrastructure
- Marketplace preparation

## Technical Decisions Made

- **Frontend**: React + Vite + TypeScript + Zustand + Tailwind CSS + shadcn/ui
- **Package Manager**: pnpm (faster, more reliable than npm)
- **Real-time**: Server-Sent Events (SSE)
- **Auth**: localStorage for SaaS, env vars for Docker
- **Logging**: Comprehensive with 30-day retention
- **Deployment**: Docker + Cloud (Railway/Vercel)
- **Git Strategy**: `feature/web-deployment` branch → merge to main

**Branch Strategy**: Work on `feature/web-deployment` branch, merge when phases complete
