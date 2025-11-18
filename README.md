# EchoChamber Analyst

**Continuous Market-Conversation Intelligence via Multi-Agent AI**

A multi-agent AI platform that scouts, ranks, and distills hidden conversations from niche online communities to provide actionable market intelligence for brands.

---

## 🚀 Quick Start

### Local Development
```bash
# Clone the repository
git clone https://github.com/jithinkrn/echo_chamber_analyst.git
cd echo_chamber_analyst

# Start development environment
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/api
# Admin: http://localhost:8000/admin
```

### Production Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md) for complete AWS ECS deployment instructions.

---

## 📊 Technology Stack

### Backend
- **Framework**: Django 5.2 + Django REST Framework
- **Database**: PostgreSQL 17 with pgvector extension
- **Cache/Queue**: Redis + Celery for background tasks
- **AI/ML**: LangGraph + LangChain + OpenAI GPT-4
- **Monitoring**: LangSmith for AI observability

### Frontend
- **Framework**: Next.js 14 + React + TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Recharts for data visualization
- **Authentication**: JWT tokens

### Deployment
- **Platform**: AWS ECS Fargate
- **CI/CD**: GitHub Actions with OIDC authentication
- **Container Registry**: Amazon ECR
- **Load Balancer**: Application Load Balancer

---

## 🤖 Multi-Agent System

The platform uses 6 specialized AI agents powered by LangGraph:

1. **Orchestrator Agent**: Central workflow coordination via LangGraph StateGraph
2. **Scout Agent**: Tavily Search API-powered content discovery with LLM-driven queries (6-month Brand Analytics / 3-month Custom Campaigns)
3. **Data Cleaner Agent**: Advanced PII detection, spam filtering, toxicity checking, and compliance tracking
4. **Analyst Agent**: GPT-4 & o3-mini powered insight generation with 4-component influencer scoring
5. **Chatbot Agent**: Pure RAG conversational interface with pgvector embeddings and GPT-4o generation
6. **Monitoring Agent**: LangSmith integration for observability and cost tracking

### Architecture

```
React Dashboard → JWT Auth → Django API → LangGraph Workflows → Database
                                    ↓
                          LangGraph StateGraph
                                    ↓
              Scout → Cleaner → Analyst → Insights
                                    ↓
                          LangSmith Monitoring
                                    ↓
                          OpenAI GPT-4 + Tools
```

---

## 🔍 Data Collection Strategy

### Tavily Search Integration
The Scout Agent uses **Tavily Search API** for intelligent content discovery:

- **LLM-Driven Queries**: GPT-4 generates optimized search queries combining brand + pain point keywords
- **Monthly Iteration**: Searches through 6 months (Brand Analytics) or 3 months (Custom Campaigns) month-by-month
- **Keyword Deduplication**: Semantic grouping of similar pain points (e.g., "sizing issues", "fit problems" → "sizing and fit issues")
- **Source Discovery**: Automatically discovers and stores relevant Reddit communities and forums
- **Thread Extraction**: LLM analyzes search results to extract relevant discussion threads

### Collection Periods
- **Brand Analytics Campaigns**: 6 months of comprehensive historical data
- **Custom Strategic Campaigns**: 3 months of focused, objective-driven data
- **Scheduled Updates**: Celery Beat tasks run hourly for continuous monitoring

### Echo Score Calculation
Communities are ranked by relevance using a proprietary EchoScore algorithm:
- Thread volume (40%)
- Pain point intensity (30%)
- Engagement depth (30%)

---

## 🎯 Key Features

### Brand-Centric Analytics
- **Brand Management**: Manage multiple brands with competitor tracking
- **Campaign Dashboard**: Real-time analytics and performance metrics
- **Pain Point Heat Map**: Community-based issue tracking
- **Community Watchlist**: Echo score rankings with influencer identification
- **Influencer Pulse**: Micro-influencer tracking (<50k reach)

### AI-Powered Insights
- **Automated Sentiment Analysis**: Real-time conversation sentiment tracking
- **Trend Detection**: Identify growing pain points and opportunities with 6-month historical analysis
- **Influencer Discovery**: 4-component scoring (Reach, Authority, Advocacy, Relevance) for micro-influencers
- **Dashboard AI Insights**: o3-mini reasoning model generates 6 strategic insights from all KPIs
- **Compliance Tracking**: IMDA AI Governance compliance with audit trails

### Workflow Orchestration
- **LangGraph StateGraph**: Sophisticated workflow coordination
- **Conditional Routing**: Dynamic workflow paths based on data
- **Error Recovery**: Advanced retry mechanisms with circuit breakers
- **Real-time Monitoring**: Workflow status tracking via LangSmith

### Pure RAG Chatbot
- **Vector Embeddings**: PostgreSQL pgvector for semantic search across all content
- **Intent Classification**: GPT-4o-mini routes queries (conversational/semantic/keyword/combined)
- **Query Rewriting**: Context-aware enhancement using conversation history
- **Dual Search Modes**: Pure semantic similarity OR semantic + keyword matching (both in vector space)
- **GPT-4o Generation**: Natural language responses synthesized from retrieved context
- **Source Attribution**: Top results with similarity scores from vector search

---

## 📁 Project Structure

```
echo_chamber_analyst/
├── backend/                    # Django backend
│   ├── api/                   # API endpoints
│   ├── agents/                # LangGraph agents (Scout, Analyst, Chatbot, etc.)
│   ├── common/                # Shared models and utilities
│   ├── config/                # Django settings + Celery configuration
│   ├── Dockerfile.prod        # Production backend Dockerfile
│   └── Dockerfile.celery      # Celery worker Dockerfile
├── frontend/                   # Next.js frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── app/              # Next.js app router
│   │   └── lib/              # Utilities
│   └── Dockerfile             # Frontend Dockerfile
├── .github/
│   └── workflows/
│       └── deploy-ecs.yml     # GitHub Actions CI/CD
├── docker-compose.yml          # Development environment
├── docker-compose.prod.yml     # Production testing
├── README.md                   # This file
├── DATAFLOW.md                # Complete agent workflow documentation
├── DASHBOARD.md               # Dashboard KPI calculation formulas
└── DEPLOYMENT.md              # AWS ECS deployment guide
```

---

## 🔧 Development

### Prerequisites
- Docker Desktop
- Node.js 20+
- Python 3.12+
- PostgreSQL 17 (for local development without Docker)

### Environment Setup

1. **Backend Environment**
```bash
cd backend
cp .env.example .env
# Edit .env with your credentials
```

2. **Frontend Environment**
```bash
cd frontend
cp .env.example .env.local
# Edit .env.local with your API URL
```

3. **Required API Keys**
- OpenAI API key (for GPT-4 & o3-mini LLM features)
- Tavily API key (for Scout Agent search - required)
- LangSmith API key (for monitoring - optional)
- Reddit API credentials (for legacy scouting - optional)

### Database Migrations
```bash
# Create new migrations
docker-compose exec backend python manage.py makemigrations

# Apply migrations
docker-compose exec backend python manage.py migrate

# Create test data
docker-compose exec backend python manage.py create_test_data
```

### Create Admin User
```bash
docker-compose exec backend python manage.py create_admin_user
# Default: admin@example.com / admin123
```

---

## 🧪 Testing

### Backend Tests
```bash
docker-compose exec backend python manage.py test
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Production Build Test
```bash
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📦 Deployment

### GitHub Actions CI/CD

The project uses GitHub Actions for automated deployment to AWS ECS:

1. **OIDC Authentication**: Secure AWS access without storing credentials
2. **Docker Image Build**: Automated builds for backend, frontend, and Celery
3. **Database Migrations**: Automatic schema updates
4. **ECS Deployment**: Rolling updates to 3 services
5. **Health Checks**: Automated verification after deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete setup instructions.

---

## 🔐 Security

- **JWT Authentication**: Secure token-based authentication
- **OIDC for CI/CD**: No AWS credentials stored in GitHub
- **PII Detection**: Automatic detection and handling of personal data
- **Compliance Tracking**: Full audit trails for AI decisions
- **Security Groups**: Restricted network access in AWS
- **Secrets Management**: AWS Secrets Manager for sensitive data

---

## 📊 Monitoring & Observability

- **LangSmith**: AI workflow monitoring and debugging
- **CloudWatch Logs**: Centralized logging for all services
- **ECS Metrics**: Container health and performance metrics
- **Cost Tracking**: Token usage and API cost monitoring

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is proprietary and confidential.

---

## 🆘 Support

For issues and questions:
- Check [DEPLOYMENT.md](DEPLOYMENT.md) for deployment issues
- Review [DATAFLOW.md](DATAFLOW.md) for agent workflow details
- Check [DASHBOARD.md](DASHBOARD.md) for KPI calculation formulas
- Review GitHub Actions logs for CI/CD problems
- Check CloudWatch logs for runtime errors

---

## 📈 Project Status

**Status**: ✅ Production Ready

### Recent Updates (v2.0)
- ✅ **Tavily Search Integration**: Replaced web scraping with Tavily Search API for Scout Agent
- ✅ **Extended Collection Periods**: 6-month Brand Analytics, 3-month Custom Campaigns
- ✅ **Pure RAG Chatbot**: pgvector embeddings + GPT-4o with intent classification
- ✅ **Enhanced Analyst**: o3-mini for dashboard insights, 4-component influencer scoring
- ✅ **Advanced Cleaner**: 5 PII types, multi-layer spam filtering, toxicity detection
- ✅ **Token Optimization**: 90% reduction in LLM token usage for Brand Analytics
- ✅ **Resilient Data Saving**: Individual item error handling with comprehensive statistics
- ✅ LangGraph Migration Complete
- ✅ Brand-Centric Analytics Dashboard
- ✅ GitHub Actions OIDC Deployment
- ✅ Multi-Agent System (6 Agents)
- ✅ API Consolidation Complete
- ✅ Database Migration Automation

**Last Updated**: 2025-11-06

---

**Made with ❤️ using LangGraph, Django, and Next.js**
