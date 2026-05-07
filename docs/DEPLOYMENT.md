# Deployment Guide

Complete guide for deploying Document Assistant (Compass RAG) — Render.com cloud, Docker, and production options.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM
- 20GB+ disk space (for documentation corpus and databases)

## Option 1: Render.com (Cloud — Recommended for Demo)

Deploys both API and frontend with zero server setup. See `render_deployment.md` for the
complete step-by-step guide including env var configuration and smoke-test checklist.

**Required env var:** `ANTHROPIC_API_KEY`  
**Frontend env var (baked at build time):** `VITE_API_URL=https://<your-api>.onrender.com/api/v1`

Free tier note: instances sleep after 15 min idle; first request after sleep takes ~30-60 s.

---

## Option 2: Docker Compose (Local / Self-hosted)

### 1. Build and Start Services

```bash
# Clone or navigate to project directory
cd compass-rag

# Set environment variables
export ANTHROPIC_API_KEY=your_anthropic_key_here
export ENVIRONMENT=production

# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### 2. Verify Services

All services should be healthy after ~30 seconds:

```bash
# Check service status
docker-compose ps

# Check API health
curl http://localhost:8000/health

# Access frontend
open http://localhost:3000

# Access Grafana dashboard
open http://localhost:3001  # admin / admin
```

## Service Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │◄───────►│   Backend    │◄───────►│ PostgreSQL  │
│ (port 3000) │         │ (port 8000)  │         │ (port 5432) │
└─────────────┘         └──────────────┘         └─────────────┘
                              │
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
    ┌─────────┐         ┌──────────┐         ┌───────────┐
    │ Jaeger  │         │Prometheus│         │AlertManager│
    │ (6831)  │         │ (9090)   │         │ (9093)    │
    └─────────┘         └──────────┘         └───────────┘
                              │
                              ▼
                         ┌─────────┐
                         │ Grafana │
                         │ (3001)  │
                         └─────────┘
```

## Configuration

### Environment Variables

Create `.env` file or set environment variables:

```bash
# API Configuration (required)
ANTHROPIC_API_KEY=sk-ant-...
DEBUG=false

# Optional — for future Deepseek evaluation
# OPENROUTER_API_KEY=sk-or-...
# REASONING_MODEL=deepseek-v4

# Budget Constraints
MAX_TOOL_CALLS_PER_QUERY=20
MAX_FILE_READS_PER_QUERY=8

# Observability
JAEGER_ENABLED=true
JAEGER_HOST=jaeger
JAEGER_PORT=6831
PROMETHEUS_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

# Environment
ENVIRONMENT=production
SERVICE_VERSION=0.0.1
```

### Database Setup

PostgreSQL is automatically initialized with:
- User: `compass`
- Password: `compass_password` (change in production!)
- Database: `compass`

Run migrations (if needed):

```bash
docker-compose exec backend alembic upgrade head
```

## Monitoring

### Prometheus

Access: http://localhost:9090

**Key Metrics:**
- `compass_queries_total` — Total queries by variant and status
- `compass_query_latency_seconds` — Query response time distribution
- `compass_tool_calls_total` — Tool executions by type
- `compass_citations_total` — Citations generated
- `compass_active_sessions` — Current active sessions

### Jaeger

Access: http://localhost:16686

**Distributed Tracing:**
- View traces for API requests
- See tool execution timing
- Identify performance bottlenecks

### Grafana

Access: http://localhost:3001 (admin / admin)

**Built-in Dashboards:**
- **Compass Overview** — Query rates, success rates, latency
- Performance by variant and category
- Tool execution statistics
- Citation generation metrics

### Alerts

AlertManager configured at: http://localhost:9093

**Critical Alerts:**
- High query error rate (>10% for 5 min)
- Slow queries (p95 > 5s for 10 min)
- Tool call failures (>5%)
- Query latency SLO violation (p99 > 10s)

## Scaling

### Horizontal Scaling

Run multiple backend instances:

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3
    environment:
      - WORKER_ID=backend-${number}
```

Add load balancer (nginx):

```bash
docker run -d -p 8000:8000 nginx:alpine
# Configure nginx to round-robin to backend instances
```

### Performance Tuning

```bash
# Increase connection pool
docker-compose exec backend python -c \
  "from compass.config import settings; settings.database_pool_size = 20"

# Adjust batch sizes in evaluation harness
python scripts/run_evaluation.py --batch-size 20

# Enable query caching
docker-compose exec backend redis-server
```

## Backup & Recovery

### PostgreSQL Backup

```bash
# Backup database
docker-compose exec postgres pg_dump -U compass compass > backup.sql

# Restore database
docker-compose exec -T postgres psql -U compass compass < backup.sql
```

### Volume Backups

```bash
# Backup volumes
docker run --rm \
  -v compass-rag_postgres_data:/source \
  -v /backup:/target \
  ubuntu tar czf /target/postgres_backup.tar.gz -C /source .
```

### Session & Audit Logs

```bash
# Backup session data
docker cp compass-backend:/app/compass_sessions ./backups/sessions_$(date +%Y%m%d).tar.gz

# Backup audit logs
docker cp compass-backend:/app/compass_audit ./backups/audit_$(date +%Y%m%d).tar.gz
```

## Health Checks

### Manual Health Checks

```bash
# API health
curl http://localhost:8000/health

# Frontend health
curl http://localhost:3000

# Database health
docker-compose exec postgres pg_isready -U compass

# Prometheus health
curl http://localhost:9090/-/healthy
```

### Automated Monitoring

Each service has health checks configured in `docker-compose.yml`:

```bash
# View health status
docker-compose ps

# Restart unhealthy services
docker-compose up -d --no-deps --no-build backend
```

## Troubleshooting

### Backend Not Starting

```bash
# Check logs
docker-compose logs backend

# Verify API key
echo $ANTHROPIC_API_KEY

# Check database connectivity
docker-compose logs postgres
docker-compose exec backend python -c \
  "from compass.config import settings; print(settings.database_url)"
```

### High Latency

1. Check Prometheus for slow queries
2. Review Jaeger traces for bottlenecks
3. Monitor tool execution times
4. Check PostgreSQL query logs:
   ```bash
   docker-compose exec postgres \
     tail -f /var/log/postgresql/postgresql.log
   ```

### Memory Issues

```bash
# Check container memory usage
docker stats

# Increase memory limit in docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Database Deadlocks

```bash
# Check active queries
docker-compose exec postgres psql -U compass -c \
  "SELECT * FROM pg_stat_activity;"

# Kill long-running queries
docker-compose exec postgres psql -U compass -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE duration > interval '10 minutes';"
```

## Production Checklist

- [ ] Set strong PostgreSQL password
- [ ] Set `ANTHROPIC_API_KEY` to production key
- [ ] Set `DEBUG=false`
- [ ] Configure SSL/TLS for frontend and API
- [ ] Set up external alerting (email, Slack, PagerDuty)
- [ ] Configure log aggregation (ELK, Datadog)
- [ ] Set up automated backups
- [ ] Configure monitoring alerting thresholds
- [ ] Test disaster recovery procedures
- [ ] Document runbooks for common issues
- [ ] Set up CI/CD deployment pipeline

## SSL/TLS Setup

### Self-Signed Certificate

```bash
# Generate certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365

# Configure nginx for HTTPS
docker run -d -p 443:443 \
  -v /path/to/cert.pem:/etc/nginx/cert.pem \
  -v /path/to/key.pem:/etc/nginx/key.pem \
  nginx:alpine
```

### Let's Encrypt with Certbot

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Get certificate
certbot certonly --standalone -d your.domain.com

# Auto-renew
certbot renew --quiet --no-eff-email
```

## Logging

### View Real-Time Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend

# With timestamps
docker-compose logs -f --timestamps backend
```

### Log Aggregation

Configure in `docker-compose.yml` logging driver:

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Cleanup

### Stop All Services

```bash
docker-compose down
```

### Remove All Data

```bash
docker-compose down -v
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

## Next Steps

1. Review metrics in Grafana dashboard
2. Set up alerting rules for your thresholds
3. Configure log aggregation service
4. Implement automated backup strategy
5. Test disaster recovery procedures
6. Document custom configurations
7. Set up CI/CD deployment pipeline

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Review Grafana dashboard for metrics
3. Check Jaeger for trace details
4. Verify environment variables
5. Consult troubleshooting section above
