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
- **Framework**: Next.js 15 + React + TypeScript
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
2. **Scout Agent**: Content discovery from Reddit and web with EchoScore calculation
3. **Data Cleaner Agent**: PII detection, spam filtering, and compliance tracking
4. **Analyst Agent**: LLM-powered insight generation and influencer identification
5. **Chatbot Agent**: RAG-based conversational interface with contextual retrieval
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

## 🎯 Key Features

### Brand-Centric Analytics
- **Brand Management**: Manage multiple brands with competitor tracking
- **Campaign Dashboard**: Real-time analytics and performance metrics
- **Pain Point Heat Map**: Community-based issue tracking
- **Community Watchlist**: Echo score rankings with influencer identification
- **Influencer Pulse**: Micro-influencer tracking (<50k reach)

### AI-Powered Insights
- **Automated Sentiment Analysis**: Real-time conversation sentiment tracking
- **Trend Detection**: Identify growing pain points and opportunities
- **Influencer Discovery**: Find relevant micro-influencers in niche communities
- **Compliance Tracking**: IMDA AI Governance compliance with audit trails

### Workflow Orchestration
- **LangGraph StateGraph**: Sophisticated workflow coordination
- **Conditional Routing**: Dynamic workflow paths based on data
- **Error Recovery**: Advanced retry mechanisms with circuit breakers
- **Real-time Monitoring**: Workflow status tracking via LangSmith

---

## 📁 Project Structure

```
echo_chamber_analyst/
├── backend/                    # Django backend
│   ├── api/                   # API endpoints
│   ├── common/                # Shared models and utilities
│   ├── config/                # Django settings
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
└── DEPLOYMENT.md              # Deployment guide
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
- OpenAI API key (for LLM features)
- LangSmith API key (for monitoring - optional)
- Reddit API credentials (for content scouting - optional)

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
- Review GitHub Actions logs for CI/CD problems
- Check CloudWatch logs for runtime errors

---

## 📈 Project Status

**Status**: ✅ Production Ready

### Recent Updates
- ✅ LangGraph Migration Complete
- ✅ Brand-Centric Analytics Dashboard
- ✅ GitHub Actions OIDC Deployment
- ✅ Multi-Agent System (6 Agents)
- ✅ API Consolidation Complete
- ✅ Database Migration Automation

**Last Updated**: 2025-10-18

---

## 🎯 Roadmap

- [ ] Advanced influencer scoring algorithm
- [ ] Multi-platform support (Twitter, LinkedIn)
- [ ] Real-time notifications for brand mentions
- [ ] Custom alert configurations
- [ ] Export reports to PDF/Excel
- [ ] API rate limiting and throttling
- [ ] Multi-tenancy support

---

**Made with ❤️ using LangGraph, Django, and Next.js**
