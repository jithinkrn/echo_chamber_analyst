# EchoChamber Analyst

**Continuous Market-Conversation Intelligence via Multi-Agent AI**

A multi-agent AI platform that scouts, ranks, and distills hidden conversations from niche online communities to provide actionable market intelligence for brands.

---

### Local Development (Manual Requirements Setup)

See the [Local Development Setup](#-local-development-setup-manual) section below for detailed manual installation instructions.

---

## 📋 Prerequisites

### Required Software
- **Docker Desktop** (if using Docker Compose - recommended)
- **Python 3.12+** (for local backend development)
- **Node.js 20+** (for frontend development)
- **PostgreSQL 17** with pgvector extension (for local development without Docker)
- **Redis 7+** (for caching and Celery task queue)

### Required API Keys

Before running the application, you'll need to obtain these API keys:

1. **OpenAI API Key** (Required)
   - **Purpose**: Powers GPT-4, GPT-4o, o3-mini models in all agents
   - **Get it from**: https://platform.openai.com/api-keys
   - **Cost**: Pay-as-you-go (estimated $50-100/month per brand)

2. **Tavily API Key** (Required)
   - **Purpose**: Scout Agent's LLM-driven web search capabilities
   - **Get it from**: https://tavily.com
   - **Cost**: ~$20-30/month per brand

3. **LangSmith API Key** (Optional, but recommended)
   - **Purpose**: AI workflow monitoring, debugging, and observability
   - **Get it from**: https://smith.langchain.com
   - **Cost**: Free tier available

4. **Reddit API Credentials** (Optional)
   - **Purpose**: Legacy Reddit scraping (Tavily is now the primary source)
   - **Get it from**: https://www.reddit.com/prefs/apps
   - **Cost**: Free

---

## 🐳 Docker Compose Setup (Recommended)

Docker Compose automatically manages all services, databases, and dependencies.

### Services Included

The `docker-compose.yml` file starts 6 services:

1. **postgres**: PostgreSQL 15 with pgvector extension
2. **redis**: Redis 7 for caching and Celery message broker
3. **backend**: Django application server (port 8000)
4. **celery-worker**: Background task processor for Scout and Analyst agents
5. **celery-beat**: Periodic task scheduler for continuous monitoring
6. **frontend**: Next.js application (port 3000)

### Complete Docker Compose Workflow

```bash

# 0. Clone the repository
git clone https://github.com/jithinkrn/echo_chamber_analyst.git
cd echo_chamber_analyst

# 1. Start all services
docker-compose up -d

# 2. Check service status
docker-compose ps

# 3. Run database migrations
docker-compose exec backend python manage.py migrate

# 4. Create custom superuser for login
docker-compose exec backend python manage.py createsuperuser
# Follow prompts to set custom username, email, and password

# 5. View logs from all services
docker-compose logs -f

# 5. View logs from specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat
docker-compose logs -f frontend
```

### Stopping and Restarting

```bash
# Stop all services (preserves data)
docker-compose down

# Stop and remove volumes (WARNING: deletes all database data)
docker-compose down -v

# Restart a specific service
docker-compose restart backend

# Rebuild containers after code changes
docker-compose up -d --build
```

### Accessing Services

```bash
# Access backend Django shell
docker-compose exec backend python manage.py shell

# Access PostgreSQL database shell
docker-compose exec postgres psql -U echochamber -d echochamber_db

# Access Redis CLI
docker-compose exec redis redis-cli

# Execute Django management commands
docker-compose exec backend python manage.py <command>
```

---

## 🔧 Local Development Setup (Manual)

For more control during development, you can run services individually without Docker.

### Step 1: Clone Repository

```bash
git clone https://github.com/jithinkrn/echo_chamber_analyst.git
cd echo_chamber_analyst
```

### Step 2: Install PostgreSQL with pgvector

#### macOS (using Homebrew)

```bash
# Install PostgreSQL
brew install postgresql@17
brew services start postgresql@17

# Install pgvector extension
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
cd ..
```

#### Ubuntu/Debian

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql-17 postgresql-server-dev-17
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Install pgvector extension
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
cd ..
```

#### Create Database

```bash
# Connect to PostgreSQL
psql postgres

# Run these SQL commands:
CREATE DATABASE echochamber_db;
CREATE USER echochamber WITH PASSWORD 'your_password_here';
ALTER ROLE echochamber SET client_encoding TO 'utf8';
ALTER ROLE echochamber SET default_transaction_isolation TO 'read committed';
ALTER ROLE echochamber SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE echochamber_db TO echochamber;

# Connect to the new database and enable pgvector
\c echochamber_db
CREATE EXTENSION IF NOT EXISTS vector;

# Verify pgvector is installed
\dx

# Exit
\q
```

### Step 3: Install Redis

#### macOS

```bash
brew install redis
brew services start redis
```

#### Ubuntu/Debian

```bash
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### Verify Redis

```bash
redis-cli ping
# Should return: PONG
```

### Step 4: Backend Setup

#### Install Python Dependencies

```bash
cd backend

# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

#### Configure Environment Variables

```bash
# The .env file is already present in the backend directory
# Edit it with your credentials
nano .env  # or use your preferred editor
```

**Key environment variables to configure in `.env`:**

```bash
# Django Settings
SECRET_KEY=your-unique-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (update password if you changed it)
DATABASE_URL=postgresql://echochamber:your_password_here@localhost:5432/echochamber_db

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# OpenAI API (REQUIRED)
OPENAI_API_KEY=sk-proj-your-actual-openai-key-here

# Tavily Search API (REQUIRED)
TAVILY_API_KEY=tvly-your-actual-tavily-key-here

# LangSmith (OPTIONAL)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your-actual-langsmith-key-here
LANGSMITH_API_KEY=lsv2_pt_your-actual-langsmith-key-here
LANGCHAIN_PROJECT=echochamber-analyst
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Reddit API (OPTIONAL)
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=EchoChamberAnalyst/1.0

# CORS (update with your frontend URL)
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

#### Run Database Migrations

```bash
# With virtual environment activated
python manage.py migrate
```

#### Create Admin User

```bash
python manage.py create_admin_user
# Default credentials: admin@example.com / admin123
```

#### (Optional) Create Test Data

```bash
python manage.py create_test_data
```

#### Start Backend Server

```bash
# Make sure virtual environment is activated
python manage.py runserver 0.0.0.0:8000

# Server available at: http://localhost:8000
```

### Step 5: Start Celery Workers

Celery handles asynchronous tasks. You need both worker and beat scheduler.

**Terminal 2 - Celery Worker:**

```bash
cd backend
source venv/bin/activate
celery -A config worker --loglevel=info
```

**Terminal 3 - Celery Beat:**

```bash
cd backend
source venv/bin/activate
celery -A config beat --loglevel=info
```

### Step 6: Frontend Setup

**Terminal 4:**

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
nano .env.local
```

**`.env.local` configuration:**

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

**Start Frontend:**

```bash
npm run dev
# Frontend available at: http://localhost:3000
```

### Step 7: Verify Installation

```bash
# Backend health check
curl http://localhost:8000/api/health/

# Frontend: http://localhost:3000
# Django Admin: http://localhost:8000/admin (admin@example.com / admin123)
```

---

## 📊 Technology Stack

### Backend
- **Framework**: Django 5.2 + Django REST Framework
- **Database**: PostgreSQL 17 with pgvector extension
- **Cache/Queue**: Redis 7 + Celery
- **AI/ML**: LangGraph + LangChain + OpenAI (GPT-4, GPT-4o, o3-mini)
- **Monitoring**: LangSmith
- **Search**: Tavily Search API

### Frontend
- **Framework**: Next.js 14 + React 18 + TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Authentication**: JWT tokens

### Deployment
- **Platform**: AWS ECS Fargate
- **CI/CD**: GitHub Actions with OIDC
- **Container Registry**: Amazon ECR
- **Load Balancer**: Application Load Balancer

---

## 🤖 Multi-Agent System

The platform uses 6 specialized AI agents powered by LangGraph:

1. **Orchestrator Agent** (`agents/orchestrator.py`) - Central StateGraph coordination
2. **Scout Agent** (`agents/scout.py`) - Tavily Search API-powered content discovery
3. **Data Cleaner Agent** (`agents/datacleaner.py`) - PII detection, spam filtering, toxicity checking
4. **Analyst Agent** (`agents/analyst.py`) - GPT-4 + o3-mini insight generation
5. **Chatbot Agent** (`agents/rag_tool.py`) - RAG with pgvector and 3-layer security
6. **Monitoring Agent** (`agents/monitoring_integration.py`) - LangSmith observability

### Architecture

```
User Request → Orchestrator Agent (StateGraph)
                      ↓
         Scout Agent (Tavily Search)
                      ↓
         Data Cleaner Agent (PII, Spam, Toxicity)
                      ↓
         Analyst Agent (GPT-4 + o3-mini)
                      ↓
         Chatbot Agent (RAG with pgvector)
                      ↓
         Monitoring Agent (LangSmith)
                      ↓
              Database + Dashboard
```

---

## 🔍 Data Collection Strategy

### Tavily Search Integration

- **LLM-Driven Queries**: GPT-4 generates optimized search queries
- **Monthly Iteration**: 6-month Brand Analytics / 3-month Custom Campaigns
- **Keyword Deduplication**: Semantic grouping of similar pain points
- **Source Discovery**: Automatic Reddit/forum discovery
- **Thread Extraction**: LLM-analyzed relevant discussions

---

## 🎯 Key Features

### Brand-Centric Analytics
- Multi-brand management with competitor tracking
- Real-time campaign dashboards
- Pain point heat maps
- Community watchlist with echo scores
- Micro-influencer tracking (<50k reach)

### AI-Powered Insights
- Automated sentiment analysis
- 6-month trend detection
- 4-component influencer scoring (Reach, Authority, Advocacy, Relevance)
- o3-mini dashboard insights (6 strategic insights)
- IMDA MGF-Gen AI 2024 compliance

### RAG Chatbot
- PostgreSQL pgvector semantic search
- GPT-4o-mini intent classification
- GPT-4o response generation
- 3-layer security (Regex → LLM → Moderation API)
- Source attribution with similarity scores

---

## 📁 Project Structure

```
echo_chamber_analyst/
├── backend/
│   ├── agents/          # 6 LangGraph AI agents
│   ├── api/             # REST API endpoints
│   ├── common/          # Models and utilities
│   ├── config/          # Django + Celery config
│   ├── tests/           # 554 comprehensive tests
│   └── manage.py
├── frontend/
│   ├── src/app/         # Next.js 14 app router
│   ├── src/components/  # React components
│   └── package.json
├── docker-compose.yml   # Development environment
├── DATAFLOW.md          # Agent workflows
├── DASHBOARD.md         # KPI formulas
└── DEPLOYMENT.md        # AWS ECS guide
```

---

## 🧪 Testing

Comprehensive testing: **554 tests, 97.81% pass rate** (542 passed, 12 failed)

### Quick Test Commands

```bash
# All tests (Docker)
docker-compose exec backend python manage.py test

# All tests (local)
python manage.py test
```

### Test Categories

| Category | Tests | Pass Rate | Purpose |
|----------|-------|-----------|---------|
| **Unit Tests** | 79 | 100% | Agent logic validation |
| **Integration Tests** | 29 | 100% | Database, RAG, Celery workflows |
| **Security Tests** | 49 | 100% | OWASP vulnerabilities, LLM security |
| **LIME (Explainability)** | 4 | 100% | Word-level attribution |
| **SHAP (Explainability)** | 3 | 100% | Feature importance |
| **AIF360 (Fairness)** | 4 | 100% | Bias detection (SPD=0.0, DI=1.0) |
| **Promptfoo Red Team** | 384 | 96.88% | Adversarial robustness |
| **Promptfoo Intent** | 50 | 100% | Intent classification accuracy |
| **TOTAL** | **554** | **97.81%** | Comprehensive coverage |

### Run Specific Tests

```bash
# Unit tests
pytest backend/tests/unit_test/ -v

# Security tests
pytest backend/tests/security_tests/ -v

# XAI tests (LIME, SHAP, AIF360)
bash backend/tests/run_lime_tests.sh
bash backend/tests/run_shap_tests.sh
bash backend/tests/run_aif360_tests.sh

# Promptfoo adversarial tests
bash backend/tests/run_promptfoo_tests.sh

# All XAI tests
bash backend/tests/run_all_xai_tests.sh
```

---

## 📦 Deployment

### AWS ECS Production Deployment

GitHub Actions automates deployment to AWS ECS:

1. **OIDC Authentication** - Secure AWS access
2. **Docker Image Build** - Backend, frontend, Celery
3. **Database Migrations** - Automatic schema updates
4. **ECS Deployment** - Rolling updates to 3 services
5. **Health Checks** - Automated verification

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete setup.

---

## 🔐 Security

### Application Security
- JWT authentication
- PII detection (5 types)
- SQL injection prevention (Django ORM)
- XSS protection (CSP headers)
- CSRF protection

### LLM Security
**3-Layer Defense:**
1. Intent classification (preemptive)
2. Regex patterns (zero latency)
3. LLM boundaries (nuanced reasoning)
4. OpenAI Moderation API (independent validation)

**Results:** 96.88% adversarial robustness (384 tests), 100% intent classification (50 tests)

### Infrastructure Security (AWS)
- OIDC for CI/CD
- Security groups (restricted access)
- AWS Secrets Manager
- VPC isolation
- TLS/SSL enforcement

---

## 📊 Monitoring & Observability

### LangSmith Integration

```bash
# Enable in .env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-key-here
LANGCHAIN_PROJECT=echochamber-analyst
```

View traces at: https://smith.langchain.com

### Logs

```bash
# Docker logs
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Production (AWS CloudWatch)
# - ECS service logs
# - RDS metrics
# - ALB metrics
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Backend Connection Refused
```bash
docker-compose ps
docker-compose logs backend
docker-compose restart backend
```

#### 2. Database Migration Errors
```bash
docker-compose down -v  # WARNING: Deletes data
docker-compose up -d
docker-compose exec backend python manage.py migrate
```

#### 3. Celery Tasks Not Running
```bash
docker-compose logs celery-worker
docker-compose restart celery-worker celery-beat
```

#### 4. pgvector Extension Not Found
```bash
docker-compose exec postgres psql -U echochamber -d echochamber_db
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

#### 5. OpenAI Rate Limits
- Check usage: https://platform.openai.com/usage
- Reduce concurrency: `celery -A config worker --concurrency=2`

#### 6. Frontend Connection Issues
```bash
# Check backend/.env
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Check frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api

docker-compose restart backend frontend
```

#### 7. npm Install Failures
```bash
cd frontend
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and run tests
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push (`git push origin feature/amazing-feature`)
6. Open Pull Request

---

## 📝 License

This project is proprietary and confidential.

---

## 📈 Project Status

**Status**: ✅ Production Ready
**Last Updated**: 2025-11-18
