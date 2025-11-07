# Echo Chamber Analyst - Complete System Architecture Analysis

**Project Version**: 2.0  
**Last Updated**: November 7, 2025  
**Technology Stack**: LangGraph + Next.js + Django + PostgreSQL + Redis + AWS ECS

---

## Table of Contents

1. [Layered Architecture Overview](#1-layered-architecture-overview)
2. [Technology Stack Details](#2-technology-stack-details)
3. [Data Management & Database Design](#3-data-management--database-design)
4. [AI/LLM Integration](#4-aillm-integration)
5. [Deployment & Infrastructure](#5-deployment--infrastructure)
6. [Component Communication](#6-component-communication)
7. [Security & Compliance](#7-security--compliance)

---

## 1. Layered Architecture Overview

### 1.1 Presentation Layer (Frontend)

**Framework**: Next.js 15.5.3 with React 19.1.0  
**Location**: `/frontend`

**Key Technologies**:
- React 19.1.0 for UI components
- TypeScript 5 for type safety
- Tailwind CSS 4 for styling
- Recharts 3.2.1 for data visualization
- Axios 1.12.2 for HTTP requests
- Next.js Turbopack for fast development builds

**Build Output**: 
- Multi-stage Docker build (3 stages: deps, builder, runner)
- Node.js 20-alpine base image
- Static Next.js standalone binary deployment
- Optimized production bundle

**Features**:
- Server-side rendering (SSR) with Next.js
- API route integration via NEXT_PUBLIC_API_URL
- Interactive dashboards for brand analytics
- Real-time metrics visualization
- Campaign management interface

### 1.2 API Gateway & Backend Layer

**Framework**: Django 5.2.7 + Django REST Framework 3.16.1  
**Location**: `/backend`  
**Language**: Python 3.12

**Components**:
- API endpoints (RESTful)
- Authentication & Authorization (JWT)
- Health check endpoints for ALB
- Campaign management
- Dashboard KPI calculations

**Key Libraries**:
- djangorestframework (3.16.1) - REST API framework
- djangorestframework_simplejwt (5.5.1) - JWT authentication
- django-cors-headers (4.9.0) - CORS support
- drf-spectacular (0.28.0) - OpenAPI documentation
- django-filter (25.2) - Advanced filtering

### 1.3 Orchestration & Agent Layer

**Framework**: LangGraph 0.3.34  
**Location**: `/backend/agents`

**Components**:

#### 3.3.1 Workflow Orchestrator
- **File**: `orchestrator.py`
- **Purpose**: Main LangGraph workflow implementation
- **Features**:
  - StateGraph-based workflow (replaces custom agents)
  - Conditional routing between nodes
  - Parallel execution capabilities
  - Memory checkpoint persistence (MemorySaver)
  - Sophisticated workflow decision routing

#### 3.3.2 State Management
- **File**: `state.py`
- **State Classes**:
  - `EchoChamberAnalystState` - Main workflow state
  - `CampaignContext` - Campaign-specific data
  - `TaskStatus` enum - Task execution states
  - `ContentType` enum - Content classification
  - `InsightType` enum - Insight categorization

#### 3.3.3 Node Implementations
- **File**: `nodes.py`
- **Nodes**:
  - `scout_node` - Real-time content discovery
  - `cleaner_node` - Content cleaning & preprocessing
  - `analyst_node` - AI-powered analysis
  - `chatbot_node` - Chat interaction handling
  - `monitoring_node` - Workflow monitoring

#### 3.3.4 Tools Integration
- **File**: `tools.py`
- **Tools Available**:
  - Database query tools
  - Content search tools
  - RAG (Retrieval-Augmented Generation) tools
  - Vector search tools
  - Dashboard analytics tools
  - Influencer analysis tools
  - Pain point analysis tools

#### 3.3.5 Additional Agent Modules
- **embedding_service.py** - OpenAI embeddings (text-embedding-3-small)
- **rag_tool.py** - Retrieval-Augmented Generation
- **vector_tools.py** - Vector similarity search
- **dashboard_tools.py** - Dashboard KPI generation
- **scout_data_collection.py** - Real-time data collection
- **analyst.py** - Unified content & influencer analysis
- **monitoring.py** - Workflow monitoring & callbacks
- **retry.py** - Resilient execution with retries
- **error_handling.py** - Error recovery mechanisms

### 1.4 Task Queue & Async Processing

**Framework**: Celery 5.5.3  
**Message Broker**: Redis (using RQ protocol)  
**Result Backend**: Redis  
**Location**: `/backend/config/celery.py`

**Task Scheduler**: Celery Beat (scheduled tasks)

**Periodic Tasks** (defined in celery.py):
```
1. check_and_execute_scheduled_campaigns - Every 60s
2. update_dashboard_metrics_task - Every 300s (5 min)
3. cleanup_old_data_task - Daily
4. generate_daily_insights_task - Daily
5. check_and_complete_campaigns - Every 10 min
```

**Worker Configuration**:
- Concurrency: 2 workers
- Max tasks per child: 1000
- Loglevel: INFO

### 1.5 Data Layer

#### 1.5.1 Primary Database: PostgreSQL 15+

**Location**: Cloud-hosted RDS (AWS)  
**Connection**: `psycopg` 3.2.10 (async-capable)  
**DSN Format**: `postgresql://user:pass@host:port/dbname`

**Key Extensions**:
- `pgvector` (0.4.1) - Vector similarity search
- UUID support for primary keys
- Full-text search capabilities
- JSON field support

**Models Implemented**:
1. **Brand** - Company/brand being analyzed
2. **Competitor** - Competitor brands
3. **Campaign** - Marketing campaigns with custom/automatic types
4. **Source** - Data sources (Reddit, forums, etc.)
5. **Community** - Reddit communities, Discord servers
6. **Thread** - Individual forum threads/posts
7. **RawContent** - Unprocessed content
8. **ProcessedContent** - Cleaned & preprocessed content
9. **PainPoint** - Extracted pain points with intensity
10. **Influencer** - Identified influencers with scores
11. **Insight** - Generated AI insights
12. **DashboardMetrics** - KPI metrics for dashboards
13. **AuditLog** - Compliance & audit trails
14. **AgentMetrics** - Agent performance metrics

#### 1.5.2 Vector Database Integration

**Technology**: pgvector (PostgreSQL extension)  
**Embedding Model**: OpenAI text-embedding-3-small
- Dimensions: 1536
- Cost: $0.02 per 1M tokens

**Vector Fields**:
- Thread embeddings
- Content embeddings
- Insight embeddings
- Pain point embeddings

**Similarity Search**: 
- IVFFlat indexing for efficient searches
- Cosine distance metrics
- Batch operations support

#### 1.5.3 Caching Layer: Redis

**Technology**: Redis 7-alpine  
**Purpose**: 
- Celery message broker (Database 1)
- Celery result backend (Database 0)
- Session caching
- Rate limiting
- Data cache

**Configuration**:
- Host: redis (Docker) or AWS ElastiCache
- Port: 6379
- Persistence: RDB snapshots (--appendonly yes)

---

## 2. Technology Stack Details

### 2.1 Frontend Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 15.5.3 | React framework with SSR |
| React | 19.1.0 | UI library |
| TypeScript | 5 | Type safety |
| Tailwind CSS | 4 | Utility-first CSS |
| Recharts | 3.2.1 | React charting library |
| Axios | 1.12.2 | HTTP client |
| Headless UI | 2.2.8 | Unstyled components |
| Heroicons | 2.2.0 | Icon library |
| Lucide React | 0.544.0 | Additional icons |
| React Markdown | 10.1.0 | Markdown rendering |

### 2.2 Backend Stack

#### Django & Web Framework
| Technology | Version | Purpose |
|-----------|---------|---------|
| Django | 5.2.7 | Web framework |
| DRF | 3.16.1 | REST API |
| Gunicorn | 21.2.0 | WSGI application server |
| dj-database-url | 3.0.1 | Database URL parsing |
| django-cors-headers | 4.9.0 | CORS support |
| django-filter | 25.2 | Filtering |
| drf-spectacular | 0.28.0 | OpenAPI schema |

#### Database & ORM
| Technology | Version | Purpose |
|-----------|---------|---------|
| psycopg | 3.2.10 | PostgreSQL adapter (async) |
| psycopg-binary | 3.2.10 | Pre-compiled adapter |
| pgvector | 0.4.1 | Vector support |
| SQLAlchemy | 2.0.44 | ORM/query builder |
| sqlparse | 0.5.3 | SQL parsing |

#### AI/LLM Technologies
| Technology | Version | Purpose |
|-----------|---------|---------|
| OpenAI | 1.109.1 | LLM API (GPT-4) |
| LangChain | 0.3.27 | LLM framework |
| LangChain-Core | 0.3.79 | Core abstractions |
| LangChain-OpenAI | 0.2.14 | OpenAI integration |
| LangChain-Community | 0.3.18 | Community tools |
| LangChain-Text-Splitters | 0.3.11 | Text chunking |
| **LangGraph** | **0.3.34** | **Workflow orchestration** |
| LangGraph-Checkpoint | 2.1.2 | State persistence |
| LangGraph-Prebuilt | 0.1.8 | Prebuilt agents |
| LangGraph-SDK | 0.1.74 | LangGraph SDK |
| LangSmith | 0.3.45 | LLM observability |

#### Async & Task Processing
| Technology | Version | Purpose |
|-----------|---------|---------|
| Celery | 5.5.3 | Async task queue |
| Redis | 6.4.0 | Cache & broker |
| asyncio | Built-in | Async runtime |
| aiohttp | 3.13.1 | Async HTTP client |

#### Search & Scraping
| Technology | Version | Purpose |
|-----------|---------|---------|
| DuckDuckGo (ddgs) | 9.6.1 | Web search API |
| Tavily | 0.7.12 | Enhanced search |
| BeautifulSoup4 | 4.14.2 | HTML parsing |
| lxml | 6.0.2 | XML/HTML processing |
| Requests | 2.32.5 | HTTP library |

#### Data Processing
| Technology | Version | Purpose |
|-----------|---------|---------|
| Pydantic | 2.12.3 | Data validation |
| Pydantic-Settings | 2.11.0 | Settings management |
| NumPy | 2.3.4 | Numerical computing |
| Pandas | (as needed) | Data manipulation |

#### Authentication & Security
| Technology | Version | Purpose |
|-----------|---------|---------|
| djangorestframework_simplejwt | 5.5.1 | JWT auth |
| PyJWT | 2.10.1 | JWT signing |
| Cryptography | 46.0.3 | Encryption |

#### Monitoring & Logging
| Technology | Version | Purpose |
|-----------|---------|---------|
| LangSmith | 0.3.45 | AI agent monitoring |
| Python logging | Built-in | Application logging |

#### Other Dependencies
| Technology | Version | Purpose |
|-----------|---------|---------|
| python-dotenv | 1.1.1 | Environment variables |
| tenacity | 9.1.2 | Retry logic |
| tiktoken | 0.12.0 | Token counting |
| tqdm | 4.67.1 | Progress bars |
| PyYAML | 6.0.3 | YAML parsing |

---

## 3. Data Management & Database Design

### 3.1 Database Architecture

```
PostgreSQL 15+ (AWS RDS)
├── pgvector Extension (Vector embeddings)
├── Full-text search
├── JSON field support
└── UUID primary keys
```

### 3.2 Data Models Hierarchy

```
Core Business Models:
├── Brand (company being analyzed)
│   ├── Competitors
│   ├── Campaigns (automatic brand analytics)
│   ├── Communities (Reddit, forums)
│   └── Sources (data collection sources)
│
├── Campaign (marketing campaign)
│   ├── Threads (discussions)
│   ├── Communities (monitored)
│   ├── Pain Points (extracted)
│   ├── Influencers (identified)
│   └── Insights (AI-generated)
│
├── Community (forum/subreddit)
│   ├── Echo Score (calculated)
│   ├── Pain Points (aggregated)
│   ├── Influencers (active members)
│   └── Threads (discussions)
│
├── Thread (post/discussion)
│   ├── Vector Embeddings (pgvector)
│   ├── Comments/Replies
│   ├── Author (Influencer reference)
│   ├── Sentiment Analysis
│   └── Pain Point Tags

Analytic Models:
├── PainPoint (extracted user problems)
│   ├── Intensity Score
│   ├── Frequency Count
│   ├── Trend Analysis
│   └── Influencer Mentions
│
├── Influencer (identified users)
│   ├── Reach Score
│   ├── Authority Score
│   ├── Advocacy Score
│   ├── Relevance Score
│   └── Overall Influence Score
│
├── Insight (AI-generated insights)
│   ├── Type (Pain Point, Trend, Sentiment, etc.)
│   ├── Confidence Score
│   ├── Priority Score
│   └── Strategic Importance
│
├── DashboardMetrics (KPI aggregations)
│   ├── Campaign metrics
│   ├── Community health
│   ├── Sentiment trends
│   └── Influencer rankings
│
└── AuditLog (compliance tracking)
    ├── Action type
    ├── Agent name
    ├── Timestamp
    └── Metadata
```

### 3.3 Vector Embedding Strategy

**Model**: OpenAI text-embedding-3-small
**Dimensions**: 1536
**Batch Size**: 100 items per request
**Cost**: $0.02 per 1M tokens

**Embedded Fields**:
1. **Thread embeddings** - For semantic search across discussions
2. **Content embeddings** - For RAG retrieval
3. **Insight embeddings** - For similarity-based insight grouping
4. **Pain point embeddings** - For clustering similar issues

**Index Strategy**:
- IVFFlat index for large-scale similarity search
- Cosine distance metric
- Partial indexing (on_conflict: ignore duplicates)

### 3.4 Caching Strategy

**Redis Architecture**:
```
Redis Database 0: Celery Results
├── Task results (TTL-based)
├── Cache layer
└── Rate limiting

Redis Database 1: Celery Broker
├── Task queue
└── Message passing
```

**Cache Keys**:
- `campaign:{campaign_id}:metrics` - Dashboard KPIs
- `community:{community_id}:echo_score` - Community scores
- `influencer:{username}:profile` - Influencer data
- `search:{query}:results` - Search results
- `rate_limit:{user}:{resource}` - Rate limit tracking

---

## 4. AI/LLM Integration

### 4.1 LangGraph Workflow Architecture

```
LangGraph Workflow
├── Entry Point: "start" node
│
├── Routing Decision (determine_workflow_type)
│   ├── "content_analysis" → route_workflow
│   ├── "chat_query" → chatbot_node
│   └── "error" → error_handler
│
├── Content Processing Path
│   ├── route_workflow (conditional)
│   │   ├── "scout_first" → scout_node
│   │   ├── "parallel_processing" → parallel_orchestrator
│   │   ├── "analysis_only" → analyze_content
│   │   └── "error" → error_handler
│   │
│   ├── scout_node (real-time data collection)
│   │   └── Edge → cleaner_node
│   │
│   ├── cleaner_node (preprocessing)
│   │   └── Edge → analyze_content
│   │
│   ├── analyze_content (AI analysis)
│   │   └── Edge → workflow_monitor
│   │
│   ├── workflow_monitor (monitoring)
│   │   └── Edge → finalize_workflow
│   │
│   └── finalize_workflow (results aggregation)
│       └── Edge → END
│
├── Chat Processing Path
│   ├── chatbot_node
│   │   └── Edge → finalize_workflow
│
├── Error Handling
│   ├── error_handler
│   │   └── Edge → finalize_workflow
│
└── Parallel Processing
    ├── parallel_orchestrator (concurrent execution)
    │   └── Edge → workflow_monitor
```

### 4.2 LangChain Integration

**LLM Models**:
- **Primary**: GPT-4 (gpt-4)
  - Temperature: 0.3 (for analysis)
  - Max tokens: 2000-3000
  - Purpose: Insight generation, analysis

**Tools for Agents**:
1. **Database Query Tool** - SQL execution
2. **Content Search Tool** - Full-text search
3. **RAG Tool** - Document retrieval
4. **Vector Search Tool** - Semantic search
5. **Hybrid Search Tool** - Combined search
6. **Dashboard Tools** - KPI calculation
7. **Influencer Tools** - Scoring & analysis
8. **Pain Point Tools** - Extraction & clustering

### 4.3 LangSmith Integration

**Purpose**: AI agent observability and monitoring

**Configuration**:
```python
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')
LANGSMITH_PROJECT = 'echochamber-analyst'
LANGSMITH_ENDPOINT = 'https://api.smith.langchain.com'
LANGCHAIN_TRACING_V2 = True
```

**Monitoring Features**:
- Trace execution paths
- Monitor token usage
- Track latency
- Identify bottlenecks
- Cost analysis

### 4.4 Embedding Service

**File**: `backend/agents/embedding_service.py`

**Capabilities**:
- Single embedding generation
- Batch embedding (up to 2048 items)
- Dimension control (1536)
- Token counting
- Cost tracking
- Error handling & retry

```python
class EmbeddingService:
    model = "text-embedding-3-small"
    dimensions = 1536
    batch_size = 100
```

---

## 5. Deployment & Infrastructure

### 5.1 AWS Architecture

```
AWS Region: ap-southeast-1 (Singapore)

├── EC2 Container Registry (ECR)
│   ├── echochamber-backend:latest
│   ├── echochamber-frontend:latest
│   └── echochamber-celery-worker:latest
│
├── ECS (Elastic Container Service)
│   ├── Cluster: echochamber-cluster
│   │
│   ├── Service: echochamber-backend-service
│   │   ├── Task Definition: echochamber-backend
│   │   ├── Launch Type: Fargate
│   │   ├── Platform Version: Latest
│   │   ├── Desired Count: 2
│   │   ├── Container: backend
│   │   │   ├── Image: ECR backend:latest
│   │   │   ├── Port: 8000
│   │   │   └── CPU: 512 (1024 typical)
│   │   │       Memory: 1024 (2048 typical)
│   │   ├── Load Balancer: ALB (Application Load Balancer)
│   │   │   └── Target Group: echochamber-backend-tg
│   │   │       ├── Port: 8000
│   │   │       ├── Health Check Path: /health/
│   │   │       ├── Interval: 30s
│   │   │       ├── Timeout: 5s
│   │   │       └── Healthy Threshold: 2
│   │   └── Auto Scaling:
│   │       ├── Min: 2 tasks
│   │       ├── Max: 10 tasks
│   │       └── Target CPU: 70%
│   │
│   ├── Service: echochamber-frontend-service
│   │   ├── Task Definition: echochamber-frontend
│   │   ├── Container Port: 3000
│   │   ├── Desired Count: 2
│   │   └── Load Balancer: ALB (same ALB, different host rule)
│   │
│   └── Service: echochamber-celery-worker-service
│       ├── Task Definition: echochamber-celery-worker
│       ├── Launch Type: Fargate
│       ├── Desired Count: 2-4
│       ├── CPU: 512-1024
│       ├── Memory: 1024-2048
│       └── Auto Scaling: Based on queue depth
│
├── RDS (Relational Database Service)
│   ├── Database: PostgreSQL 15
│   ├── Instance: db.t4g.medium (typical)
│   ├── Storage: 100GB+ with auto-scaling
│   ├── Backups: Daily automated
│   ├── Multi-AZ: Enabled (high availability)
│   ├── Encryption: At rest and in transit
│   ├── Extensions:
│   │   ├── pgvector (vectors)
│   │   └── uuid-ossp (UUIDs)
│   └── Security Group: RDS-SG
│       └── Inbound: Port 5432 from ECS SG
│
├── ElastiCache (Redis)
│   ├── Engine: Redis 7
│   ├── Node Type: cache.t4g.micro (development) → cache.t4g.small (production)
│   ├── Cluster Mode: Disabled
│   ├── Multi-AZ: Enabled (high availability)
│   ├── Encryption: At rest and in transit
│   ├── Security Group: ElastiCache-SG
│   └── Port: 6379
│
├── Application Load Balancer (ALB)
│   ├── Scheme: Internet-facing
│   ├── Subnets: Public subnets (2+ AZs)
│   ├── Security Groups: ALB-SG
│   │   ├── Inbound:
│   │   │   ├── Port 80 (HTTP → 443 redirect)
│   │   │   └── Port 443 (HTTPS)
│   │   └── Outbound: All traffic
│   │
│   ├── Listeners:
│   │   ├── HTTP (80) → HTTPS (443) redirect
│   │   └── HTTPS (443)
│   │       ├── Certificate: ACM SSL/TLS
│   │       └── Rules:
│   │           ├── Host: api.echochamber.com → backend-tg:8000
│   │           ├── Host: echochamber.com → frontend-tg:3000
│   │           └── Path: /* → frontend-tg:3000
│   │
│   ├── Target Groups:
│   │   ├── echochamber-backend-tg (port 8000)
│   │   │   ├── Protocol: HTTP
│   │   │   ├── Health Check: /health/
│   │   │   └── Stickiness: Disabled
│   │   │
│   │   └── echochamber-frontend-tg (port 3000)
│   │       ├── Protocol: HTTP
│   │       ├── Health Check: /
│   │       └── Stickiness: Enabled (app-based)
│   │
│   └── WAF (Web Application Firewall): Optional
│       ├── SQL Injection protection
│       ├── XSS protection
│       └── Rate limiting rules
│
├── VPC (Virtual Private Cloud)
│   ├── CIDR: 10.0.0.0/16
│   ├── Public Subnets: 10.0.1.0/24, 10.0.2.0/24 (ALB)
│   ├── Private Subnets: 10.0.10.0/24, 10.0.11.0/24 (ECS, RDS, ElastiCache)
│   ├── NAT Gateway: In public subnet (for private subnet outbound)
│   └── Security Groups:
│       ├── ALB-SG
│       ├── ECS-SG (backend & celery)
│       ├── RDS-SG
│       └── ElastiCache-SG
│
├── CloudWatch (Monitoring)
│   ├── Log Groups:
│   │   ├── /ecs/echochamber-backend
│   │   ├── /ecs/echochamber-frontend
│   │   └── /ecs/echochamber-celery-worker
│   ├── Metrics: CPU, memory, network
│   ├── Alarms: Unhealthy tasks, high latency
│   └── Dashboards: Service health overview
│
├── Secrets Manager
│   ├── DATABASE_URL
│   ├── OPENAI_API_KEY
│   ├── REDIS_URL
│   ├── JWT_SECRET_KEY
│   └── Other credentials
│
└── IAM (Identity & Access Management)
    ├── ECS Task Role: S3, RDS, Secrets Manager access
    ├── GitHub Actions OIDC Role
    │   ├── ECR push permissions
    │   ├── ECS update service permissions
    │   └── RDS migration task permissions
    └── Task Execution Role: CloudWatch Logs, pull ECR
```

### 5.2 Docker Containerization

#### 5.2.1 Backend Dockerfile (Production)

**Base Image**: `python:3.12-slim`
**Components**:
- System dependencies: gcc, g++, libpq-dev, postgresql-client, curl
- Python dependencies: From requirements.txt
- Gunicorn 21.2.0 (WSGI server)
- psycopg2-binary (PostgreSQL driver)
- pgvector (vector support)
- Non-root user: appuser (UID 1000)
- Health check: Disabled (ALB handles)
- Port: 8000
- Workers: 4 (Gunicorn sync workers)
- Timeout: 120s

**Entrypoint**: `./docker-entrypoint.sh` (runs migrations)

#### 5.2.2 Celery Worker Dockerfile

**Base Image**: `python:3.12-slim`
**Components**:
- Same dependencies as backend
- Celery worker configuration
- Non-root user: celeryuser (UID 1000)
- Health check: `celery inspect ping`
- Default concurrency: 2
- Max tasks per child: 1000

#### 5.2.3 Frontend Dockerfile (Multi-stage)

**Build Stages**:
1. **deps** (node:20-alpine)
   - Install dependencies via npm ci
   
2. **builder** (node:20-alpine)
   - Copy dependencies from deps stage
   - Install build tools: python3, make, g++
   - Set env: NODE_ENV=production, NEXT_TELEMETRY_DISABLED=1
   - Build Next.js: npm run build
   
3. **runner** (node:20-alpine)
   - Copy built app from builder
   - Non-root user: nextjs (UID 1001)
   - Port: 3000
   - Health check: Disabled

### 5.3 CI/CD Pipeline

**File**: `.github/workflows/deploy-ecs.yml`

**Trigger**: 
- Push to `main` or `production` branches
- Manual workflow dispatch

**Workflow Steps**:

1. **Checkout Code**
   - Uses: actions/checkout@v4

2. **Configure AWS Credentials**
   - Method: OIDC (OpenID Connect)
   - Role: GitHub Actions ECS Deploy Role
   - Region: ap-southeast-1

3. **ECR Login**
   - Uses: aws-actions/amazon-ecr-login@v2
   - Registry: {AWS_ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com

4. **Docker Setup**
   - Uses: docker/setup-buildx-action@v3

5. **Build Backend Image**
   - File: backend/Dockerfile.prod
   - Tags: SHA and latest
   - Push to ECR: echochamber-backend

6. **Build Celery Image**
   - File: backend/Dockerfile.celery
   - Tags: SHA and latest
   - Push to ECR: echochamber-celery-worker

7. **Build Frontend Image**
   - File: frontend/Dockerfile
   - Build args: NEXT_PUBLIC_API_URL
   - Tags: SHA and latest
   - Push to ECR: echochamber-frontend

8. **Database Migrations**
   - Task: echochamber-migrate-task
   - Launch type: Fargate
   - Wait for completion
   - Verify exit code = 0

9. **Deploy Services to ECS**
   - Force new deployment for:
     - echochamber-backend-service
     - echochamber-celery-worker-service
     - echochamber-frontend-service

10. **Health Checks & Verification**
    - Wait for service stability
    - Check ALB target health
    - Display logs on failure
    - Verify deployment success

### 5.4 Environment Variables (ECS Task)

**Backend Service**:
```
DATABASE_URL=postgresql://user:pass@rds.amazonaws.com:5432/dbname
REDIS_URL=redis://elasticache.amazonaws.com:6379/0
CELERY_BROKER_URL=redis://elasticache.amazonaws.com:6379/1
OPENAI_API_KEY=sk-...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=echochamber-analyst
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=api.echochamber.com
```

**Celery Worker Service**: Same as backend

**Frontend Service**:
```
NEXT_PUBLIC_API_URL=https://api.echochamber.com/api
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

---

## 6. Component Communication

### 6.1 Request Flow Diagram

```
User Request
    ↓
Browser (http/https)
    ↓
AWS ALB (listener:443)
    ↓
[Route Decision - Host/Path Based]
    ↓
├→ Backend (api.echochamber.com) → Django @ 8000
│   ├→ REST Endpoint (DRF)
│   ├→ Authentication (JWT)
│   ├→ LangGraph Orchestrator
│   │   ├→ Agent Nodes (Scout, Analyst, etc.)
│   │   ├→ LangChain/OpenAI calls
│   │   └→ Tools (RAG, Vector Search, etc.)
│   ├→ Database (PostgreSQL via psycopg)
│   ├→ Cache (Redis via django-cache)
│   └→ Response (JSON)
│
└→ Frontend (echochamber.com) → Next.js @ 3000
    ├→ Server-side rendering
    ├→ API calls (axios → Backend)
    ├→ Component rendering
    └→ HTML response
```

### 6.2 Async Task Flow

```
API Endpoint (HTTP Request)
    ↓
Django View receives request
    ↓
Create Celery Task
    ↓
Task pushed to Redis (Broker)
    ↓
Return Task ID to client (202 Accepted)
    ↓
    ├→ Celery Worker (pulls from queue)
    │   ├→ Execute task (Scout, Analysis, etc.)
    │   ├→ Store result in Redis
    │   ├→ Update database
    │   └→ Return success/failure
    │
    └→ Client polls /status/{task_id}
        ↓
        Get result from Redis
        ↓
        Return status & data
```

### 6.3 LangGraph Execution Flow

```
API Call (e.g., /api/campaigns/{id}/analyze/)
    ↓
Create CampaignContext
    ↓
Initialize EchoChamberAnalystState
    ↓
Invoke LangGraph Workflow
    ↓
[Entry Point: "start" node]
    ↓
[Routing Decision]
    ├→ Content Analysis Path
    │   ├→ [route_workflow]
    │   ├→ [scout_node] - Real-time data collection
    │   │   ├→ Tavily Search API
    │   │   ├→ Reddit API
    │   │   └→ Store in DB
    │   ├→ [cleaner_node] - Preprocessing
    │   │   ├→ Text cleaning
    │   │   ├→ Language detection
    │   │   └→ Normalization
    │   ├→ [analyze_content] - AI Analysis
    │   │   ├→ GPT-4 calls
    │   │   ├→ Pain point extraction
    │   │   ├→ Influencer identification
    │   │   └→ Generate embeddings
    │   ├→ [workflow_monitor] - Monitoring
    │   │   ├→ Log metrics
    │   │   └→ LangSmith tracing
    │   ├→ [finalize_workflow] - Aggregation
    │   │   ├→ Compile results
    │   │   └→ Update database
    │   └→ [END]
    │
    └→ Chat Query Path
        ├→ [chatbot_node]
        ├→ [finalize_workflow]
        └→ [END]
```

---

## 7. Security & Compliance

### 7.1 Authentication & Authorization

**JWT Authentication**:
- Token type: HS256
- Access token lifetime: 60 minutes
- Refresh token lifetime: 7 days
- Token rotation: Enabled
- Blacklist after rotation: Enabled

**Authorization Levels**:
- Anonymous (AllowAny) - Health check, API root
- Authenticated (IsAuthenticated) - Protected endpoints
- Admin (IsAdminUser) - Admin operations

### 7.2 Database Security

**PostgreSQL Security**:
- Network isolation (private subnet)
- Security group restrictions (port 5432)
- Connection encryption (SSL/TLS)
- User authentication (IAM database auth)
- Secrets Manager integration

**Backup Strategy**:
- Automated daily backups
- Backup retention: 7 days
- Cross-region backup copies
- Point-in-time recovery

### 7.3 API Security

**CORS Configuration**:
- Allowed origins: localhost (dev), production domain
- Allow credentials: True
- Allowed methods: GET, POST, PUT, DELETE, OPTIONS
- Allowed headers: Authorization, Content-Type

**Rate Limiting**:
- Default: 100/hour
- Reddit API: 60/minute
- Configurable per endpoint

**Input Validation**:
- Pydantic models for request validation
- DRF serializers for data validation
- LLM security tests (prompt injection, data leakage)

### 7.4 Monitoring & Compliance

**LangSmith Tracing**:
- All LLM calls logged
- Input/output tracking
- Token usage monitoring
- Cost analysis

**Audit Logging**:
- AuditLog model for all significant actions
- Agent name tracking
- Timestamp recording
- Metadata storage

**Compliance Features**:
- PII detection (optional)
- Data retention policies
- GDPR-compliant data deletion
- Compliance reporting

---

## Summary Table

| Layer | Technology | Purpose | Status |
|-------|-----------|---------|--------|
| **Presentation** | Next.js 15.5.3 + React 19 | UI/UX | Production |
| **API Gateway** | Django 5.2.7 + DRF 3.16.1 | REST API | Production |
| **Orchestration** | LangGraph 0.3.34 | Workflow management | Production |
| **Agent Framework** | LangChain 0.3.27 | LLM integration | Production |
| **Task Queue** | Celery 5.5.3 + Redis 7 | Async processing | Production |
| **LLM** | OpenAI GPT-4 | AI analysis | Production |
| **Vector DB** | PostgreSQL + pgvector | Semantic search | Production |
| **Primary DB** | PostgreSQL 15+ RDS | Data persistence | Production |
| **Cache** | Redis 7 ElastiCache | Caching layer | Production |
| **Observability** | LangSmith | AI monitoring | Production |
| **Deployment** | AWS ECS Fargate | Container orchestration | Production |
| **CI/CD** | GitHub Actions | Automated deployment | Production |

