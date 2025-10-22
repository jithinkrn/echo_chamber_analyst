# EchoChamber Analyst - Data Flow Documentation

## Overview

This document describes the complete data flow architecture for the EchoChamber Analyst system, including all agents, their interactions, triggers, and data transformations.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTIONS                            │
├─────────────────────────────────────────────────────────────────────┤
│  1. Dashboard UI (Frontend)                                          │
│  2. API Endpoints (REST)                                             │
│  3. Manual Triggers (Admin)                                          │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR (LangGraph)                        │
│  - Workflow coordination                                             │
│  - Conditional routing                                               │
│  - Error handling & retry                                            │
│  - State management                                                  │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
         ┌──────────┐     ┌──────────┐    ┌──────────┐
         │  SCOUT   │────▶│ CLEANER  │───▶│ ANALYST  │
         │  AGENT   │     │  AGENT   │    │  AGENT   │
         └──────────┘     └──────────┘    └──────────┘
                │                               │
                │                               │
                ▼                               ▼
         ┌──────────────────────────────────────────┐
         │          MONITORING AGENT                │
         │  - Performance tracking                  │
         │  - Compliance logging                    │
         │  - Cost monitoring                       │
         └──────────────────────────────────────────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │   DATABASE    │
                         │   (PostgreSQL)│
                         └───────────────┘
```

---

## Agent Details

### 1. ORCHESTRATOR AGENT

**Location**: `backend/agents/orchestrator.py`

**Purpose**: Coordinates all workflow execution using LangGraph state machine

**Key Components**:
- `EchoChamberWorkflowOrchestrator` class
- LangGraph StateGraph with conditional routing
- MemorySaver checkpointer for state persistence
- Retry and error handling mechanisms

**Workflow Nodes**:
```python
- start                 # Initialize workflow
- route_workflow       # Determine routing strategy
- scout_content        # Data collection
- clean_content        # Data cleaning
- analyze_content      # Analysis & insights
- chatbot_node         # RAG/Chat queries
- monitoring_agent     # Performance monitoring
- parallel_orchestrator # Parallel processing
- workflow_monitor     # Workflow health checks
- error_handler        # Error recovery
- finalize_workflow    # Completion & cleanup
```

**State Management**:
- Uses `EchoChamberAnalystState` class
- Tracks: workflow_id, campaign, raw_content, cleaned_content, insights, metrics
- Persistent state via MemorySaver checkpointer

**Triggers Orchestrator**:
1. **User-initiated**: `POST /api/v1/brands/{brand_id}/analysis/`
2. **Scheduled**: Celery Beat periodic tasks
3. **Manual**: Admin dashboard triggers
4. **API**: Direct workflow API calls

---

### 2. SCOUT AGENT

**Location**: `backend/agents/nodes.py` - `scout_node()`

**Purpose**: Real-time data collection from multiple platforms

**Data Sources**:
- Reddit (via PRAW API)
- Forums (web scraping)
- Review sites
- Social media platforms

**Flow**:
```
User Trigger/Schedule
        │
        ▼
  scout_node()
        │
        ├──▶ collect_real_brand_data()
        │         │
        │         ├──▶ Reddit API (PRAW)
        │         ├──▶ Web scraping
        │         └──▶ Review aggregation
        │
        ├──▶ Extract communities
        ├──▶ Extract threads
        ├──▶ Extract pain points
        ├──▶ Calculate echo scores
        ├──▶ Detect brand mentions
        │
        ▼
  _store_brand_scout_data()
        │
        ▼
   Database Storage:
   - Communities
   - Threads
   - PainPoints
   - Campaigns
        │
        ▼
   Pass to CLEANER
```

**Input**:
- `EchoChamberAnalystState` with campaign context
- Brand name, keywords, sources
- Scout configuration (focus, depth, communities)

**Output**:
- `state.raw_content` - List of ContentItem objects
- Stored in database: Communities, Threads, PainPoints
- Metrics: collection_time, items_collected

**Triggered By**:
1. **User Action**: `POST /api/v1/brands/{id}/analysis/` (action: 'start')
2. **Direct API**: `POST /api/v1/scout/analyze/`
3. **Scheduled**: Celery task `scout_reddit_task` (hourly)
4. **Manual**: `POST /api/v1/tasks/scout/`

**Triggers Next**:
- Automatically passes to **CLEANER AGENT** via orchestrator

---

### 3. DATA CLEANER AGENT

**Location**: `backend/agents/nodes.py` - `cleaner_node()`

**Purpose**: Advanced content validation, PII removal, spam filtering

**Flow**:
```
SCOUT output (raw_content)
        │
        ▼
  cleaner_node()
        │
        ├──▶ PII Detection & Masking
        │    - Emails, phones, SSNs
        │    - GDPR/CCPA compliance
        │
        ├──▶ Spam & Bot Filtering
        │    - Pattern detection
        │    - Quality scoring
        │
        ├──▶ Content Validation
        │    - Language detection
        │    - Toxicity filtering
        │    - Authenticity checks
        │
        ├──▶ Sentiment Analysis
        │    - Context-aware scoring
        │    - Multi-dimensional analysis
        │
        ├──▶ Entity Extraction
        │    - Keywords
        │    - Topics
        │    - Named entities
        │
        ├──▶ Deduplication
        │    - Similarity detection
        │    - Content clustering
        │
        ▼
  state.cleaned_content
        │
        ▼
   Pass to ANALYST
```

**Input**:
- `state.raw_content` - Raw data from Scout
- Cleaning configuration
- Compliance rules

**Output**:
- `state.cleaned_content` - Validated ContentItem list
- Cleaning statistics (PII_masked, spam_filtered, etc.)
- Quality scores per item

**Processing**:
- Batch processing (5 items per batch)
- LLM-assisted validation
- Rule-based filtering
- Statistical analysis

**Triggered By**:
- Automatically by **ORCHESTRATOR** after Scout completes
- Edge: `scout_content → clean_content`

**Triggers Next**:
- Automatically passes to **ANALYST AGENT**

---

### 4. ANALYST AGENT

**Location**:
- LangGraph node: `backend/agents/nodes.py` - `analyst_node()`
- Enhanced functions: `backend/agents/analyst.py`

**Purpose**: AI-powered content analysis, insight generation, influencer identification

**Flow**:
```
CLEANER output (cleaned_content)
        │
        ▼
  analyst_node() (LangGraph)
        │
        ├──▶ Batch Content Analysis
        │    - Pain point detection
        │    - Praise identification
        │    - Trend analysis
        │    - Sentiment analysis
        │
        ├──▶ Insight Generation
        │    - GPT-4 powered analysis
        │    - Confidence scoring
        │    - Priority ranking
        │
        ├──▶ Influencer Detection
        │    - Key voices identification
        │    - Impact assessment
        │
        ▼
  Enhanced Analyst (analyst.py)
        │
        ├──▶ analyze_influencers_for_threads()
        │         │
        │         ├──▶ aggregate_user_metrics_from_threads()
        │         ├──▶ calculate_influence_scores()
        │         │    ├─▶ calculate_reach_score()
        │         │    ├─▶ calculate_authority_score()
        │         │    ├─▶ calculate_advocacy_score()
        │         │    └─▶ calculate_relevance_score()
        │         │
        │         ▼
        │    Influencer List with Scores
        │
        ├──▶ save_influencers_to_db()
        │         │
        │         ▼
        │    Database: Influencer records
        │
        ├──▶ link_pain_points_to_influencers()
        │         │
        │         ├──▶ Cross-reference threads
        │         ├──▶ Calculate reach per pain point
        │         ├──▶ Sentiment breakdown
        │         ├──▶ Urgency scoring (0-10)
        │         └──▶ Generate recommendations
        │         │
        │         ▼
        │    Pain Point Analysis
        │
        └──▶ generate_comprehensive_analysis_summary()
                  │
                  ├──▶ Overview metrics
                  ├──▶ Influencer breakdown
                  ├──▶ Urgent pain points
                  ├──▶ Community insights
                  ├──▶ Key actionable insights
                  │
                  ▼
             Campaign.metadata['analysis_summary']
                  │
                  ▼
            Pass to MONITORING
```

**Input**:
- `state.cleaned_content` - Validated content
- Campaign context (brand, keywords, goals)
- Analysis configuration

**Output**:
- `state.insights` - List of generated insights
- `state.influencers` - Detected influencer profiles
- Database: Influencer records, linked pain points
- Campaign.metadata['analysis_summary'] - Comprehensive summary

**Influence Score Formula**:
```
Overall Score = (Reach × 30%) + (Authority × 30%) + (Advocacy × 20%) + (Relevance × 20%)

Where each component (0-100):
- Reach: Post volume + Engagement + Community diversity
- Authority: Consistency + Quality + Engagement ratio
- Advocacy: Brand mention rate + Sentiment
- Relevance: Mention frequency + Volume + Community relevance
```

**Triggered By**:
- Automatically by **ORCHESTRATOR** after Cleaner completes
- Direct call in `control_brand_analysis` after Scout
- Edge: `clean_content → analyze_content`

**Triggers Next**:
- Automatically passes to **MONITORING AGENT**

---

### 5. MONITORING AGENT

**Location**: `backend/agents/nodes.py` - `monitoring_node()`

**Purpose**: Performance tracking, compliance logging, cost monitoring

**Flow**:
```
ANALYST output
        │
        ▼
  monitoring_node()
        │
        ├──▶ Workflow Tracking
        │    - Execution times per node
        │    - Overall workflow duration
        │    - Bottleneck detection
        │
        ├──▶ Compliance Events
        │    - GDPR/CCPA compliance
        │    - Audit trail generation
        │    - Data retention tracking
        │
        ├──▶ Performance Metrics
        │    - Content processed count
        │    - Insights generated count
        │    - Quality scores
        │    - Success rates
        │
        ├──▶ Cost Tracking
        │    - Token usage (LLM)
        │    - API calls count
        │    - Total cost calculation
        │    - Budget alerts
        │
        ├──▶ Error Logging
        │    - Failed operations
        │    - Retry attempts
        │    - Recovery status
        │
        ▼
  state.monitoring_data
        │
        ├──▶ Store in Database
        │    - DashboardMetrics
        │    - AuditLog
        │
        └──▶ External Monitoring
             - LangSmith integration
             - Metrics dashboards
```

**Input**:
- Complete workflow state
- Execution history
- Performance data

**Output**:
- `state.monitoring_data` with metrics
- Database: DashboardMetrics, audit logs
- External: LangSmith traces

**Metrics Tracked**:
- `node_execution_times`: Time spent in each node
- `compliance_events`: Regulatory compliance logs
- `performance_metrics`: Quality and efficiency scores
- `cost_tracking`: Token usage and costs
- `error_events`: Failures and recoveries

**Triggered By**:
- Automatically after **ANALYST** completes
- Edge: `analyze_content → workflow_monitor → monitoring_agent`

**Triggers Next**:
- Edge: `monitoring_agent → finalize_workflow → END`

---

## User-Initiated Triggers

### 1. Dashboard - Start Brand Analysis

**Endpoint**: `POST /api/v1/brands/{brand_id}/analysis/`

**Request**:
```json
{
  "action": "start"
}
```

**Flow**:
```
User clicks "Run Analysis"
        │
        ▼
Frontend: apiService.controlBrandAnalysis(brandId, 'start')
        │
        ▼
Backend: control_brand_analysis(request, brand_id)
        │
        ├──▶ Generate keywords from brand
        ├──▶ Get target communities
        ├──▶ Create scout_config
        │
        ├──▶ collect_real_brand_data()  [SCOUT]
        │         │
        │         ▼
        ├──▶ _store_brand_scout_data()  [SCOUT → DB]
        │
        ├──▶ analyze_influencers_for_threads()  [ANALYST]
        │         │
        │         ├──▶ aggregate_user_metrics
        │         ├──▶ calculate_influence_scores
        │         └──▶ save_influencers_to_db
        │
        ├──▶ link_pain_points_to_influencers()  [ANALYST]
        │
        └──▶ generate_comprehensive_analysis_summary()  [ANALYST]
                  │
                  ▼
             Campaign.metadata['analysis_summary']
                  │
                  ▼
            Response to Frontend
                  │
                  ▼
         Dashboard displays results
```

**Response**:
```json
{
  "brand_id": "uuid",
  "brand_name": "Brand Name",
  "analysis_status": "completed",
  "data_collected": {
    "communities": 15,
    "threads": 250,
    "pain_points": 45,
    "brand_mentions": 180,
    "influencers": 50
  },
  "enhanced_analysis": {
    "summary_generated": true,
    "key_insights_count": 7,
    "urgent_pain_points": 5
  }
}
```

### 2. Dashboard - View Analysis Summary

**Endpoint**: `GET /api/v1/brands/{brand_id}/analysis-summary/`

**Flow**:
```
User views Dashboard
        │
        ▼
Frontend: apiService.getBrandAnalysisSummary(brandId)
        │
        ▼
Backend: get_brand_analysis_summary(request, brand_id)
        │
        ├──▶ Get latest campaign
        ├──▶ Retrieve campaign.metadata['analysis_summary']
        │
        ▼
    Return summary
        │
        ▼
Frontend: Display in Dashboard components
        │
        ├──▶ AI-Powered Key Insights
        ├──▶ Urgent Pain Points with Reach
        ├──▶ Influencer Breakdown
        └──▶ Top Communities
```

### 3. Direct Scout Trigger

**Endpoint**: `POST /api/v1/scout/analyze/`

**Request**:
```json
{
  "brand_name": "Brand Name",
  "keywords": ["keyword1", "keyword2"],
  "brand_id": "uuid",
  "scout_config": {
    "focus": "comprehensive",
    "search_depth": "comprehensive",
    "target_communities": ["subreddit1", "subreddit2"]
  }
}
```

**Flow**:
```
API Call
    │
    ▼
trigger_scout_analysis()
    │
    ├──▶ collect_real_brand_data()  [SCOUT]
    │         │
    │         ├──▶ Reddit scraping
    │         ├──▶ Forum scraping
    │         └──▶ Review aggregation
    │
    └──▶ _store_brand_scout_data()  [SCOUT → DB]
```

### 4. Manual Task Triggers

**Endpoint**: `POST /api/v1/tasks/scout/`

**Request**:
```json
{
  "campaign_id": 123,
  "config": {}
}
```

**Flow**:
```
Admin triggers task
        │
        ▼
trigger_scout_task()
        │
        ▼
Celery: scout_reddit_task.delay()
        │
        ▼
Background worker executes
        │
        ▼
scout_reddit_task()
        │
        ├──▶ Get active campaigns
        ├──▶ For each campaign:
        │    └──▶ collect_real_brand_data()
        │
        └──▶ Store results in DB
```

---

## Scheduled Triggers (Celery Beat)

**Configuration**: `backend/config/celery.py`

### 1. Hourly Scout Task

**Schedule**: Every hour (3600 seconds)

**Task**: `agents.tasks.scout_reddit_task`

**Flow**:
```
Celery Beat Scheduler
        │
        ▼ (Every hour)
scout_reddit_task()
        │
        ├──▶ Query active campaigns
        │
        ├──▶ For each campaign:
        │    │
        │    ├──▶ collect_real_brand_data()  [SCOUT]
        │    │
        │    └──▶ _store_brand_scout_data()  [SCOUT → DB]
        │
        └──▶ Return statistics
```

**Purpose**:
- Automatic data collection for all active brands
- Keeps dashboard data fresh
- No user intervention required

### 2. Daily Cleanup Task

**Schedule**: Every day (86400 seconds)

**Task**: `agents.tasks.cleanup_old_data_task`

**Flow**:
```
Celery Beat Scheduler
        │
        ▼ (Daily)
cleanup_old_data_task()
        │
        ├──▶ Delete old threads (>30 days)
        ├──▶ Archive old campaigns
        ├──▶ Clean temp files
        ├──▶ Compress old logs
        │
        └──▶ Return cleanup stats
```

**Purpose**:
- Maintain database performance
- Comply with data retention policies
- Free up storage space

### 3. Daily Insights Task

**Schedule**: Every day (86400 seconds)

**Task**: `agents.tasks.generate_daily_insights_task`

**Flow**:
```
Celery Beat Scheduler
        │
        ▼ (Daily)
generate_daily_insights_task()
        │
        ├──▶ Query recent data
        ├──▶ Run trend analysis
        ├──▶ Generate insights
        ├──▶ Send notifications
        │
        └──▶ Store in database
```

**Purpose**:
- Automated daily reporting
- Trend detection
- Proactive alerts

---

## Complete Data Flow Sequence

### Scenario: User Starts Brand Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: USER INTERACTION                                        │
└─────────────────────────────────────────────────────────────────┘
    User clicks "Run Analysis" on Dashboard
            ↓
    Frontend: POST /api/v1/brands/{id}/analysis/ (action: 'start')
            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: API ENTRY POINT                                         │
└─────────────────────────────────────────────────────────────────┘
    Backend: control_brand_analysis()
            ↓
    - Get Brand from DB
    - Generate keywords
    - Create scout_config
            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: SCOUT AGENT (Data Collection)                           │
└─────────────────────────────────────────────────────────────────┘
    collect_real_brand_data(brand_name, keywords, config)
            ↓
    ┌──────────────────────────────────────┐
    │ Reddit API (PRAW)                    │
    │ - Search subreddits                  │
    │ - Fetch posts & comments             │
    │ - Extract user data                  │
    └──────────────────────────────────────┘
            ↓
    ┌──────────────────────────────────────┐
    │ Web Scraping                         │
    │ - Forum threads                      │
    │ - Review sites                       │
    │ - Social mentions                    │
    └──────────────────────────────────────┘
            ↓
    ┌──────────────────────────────────────┐
    │ Data Processing                      │
    │ - Extract communities                │
    │ - Identify threads                   │
    │ - Detect pain points                 │
    │ - Calculate echo scores              │
    │ - Track brand mentions               │
    └──────────────────────────────────────┘
            ↓
    scout_results = {
        communities: [...],
        threads: [...],
        pain_points: [...],
        brand_mentions: [...]
    }
            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: DATA STORAGE (Scout → DB)                               │
└─────────────────────────────────────────────────────────────────┘
    _store_brand_scout_data(brand, scout_results)
            ↓
    Database Writes:
    - Community.objects.create() × N
    - Thread.objects.create() × N
    - PainPoint.objects.create() × N
    - Campaign.objects.update()
            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: ANALYST AGENT (Enhanced Analysis)                       │
└─────────────────────────────────────────────────────────────────┘
    Get threads and pain_points from DB
            ↓
    ┌──────────────────────────────────────────────────────┐
    │ Sub-Step 5.1: Influencer Analysis                    │
    └──────────────────────────────────────────────────────┘
    analyze_influencers_for_threads(threads, brand, campaign)
            ↓
        aggregate_user_metrics_from_threads()
            ↓
        For each user:
            calculate_influence_scores()
                ├─▶ calculate_reach_score()
                ├─▶ calculate_authority_score()
                ├─▶ calculate_advocacy_score()
                └─▶ calculate_relevance_score()
            ↓
        influencer_list (sorted by score)
            ↓
    ┌──────────────────────────────────────────────────────┐
    │ Sub-Step 5.2: Save Influencers                       │
    └──────────────────────────────────────────────────────┘
    save_influencers_to_db(brand, campaign, influencers[:50])
            ↓
        Influencer.objects.update_or_create() × 50
            ↓
    ┌──────────────────────────────────────────────────────┐
    │ Sub-Step 5.3: Link Pain Points                       │
    └──────────────────────────────────────────────────────┘
    link_pain_points_to_influencers(pain_points, influencers, threads_map)
            ↓
        For each pain_point:
            - Find threads discussing it
            - Identify influencers in those threads
            - Calculate estimated reach
            - Categorize sentiment
            - Compute urgency score (0-10)
            - Generate recommendations
            ↓
        pain_point_analysis = {
            "pain_point_1": {
                urgency_score: 8.5,
                influencer_count: 12,
                estimated_reach: 45000,
                sentiment_breakdown: {...},
                recommended_action: "..."
            }
        }
            ↓
    ┌──────────────────────────────────────────────────────┐
    │ Sub-Step 5.4: Generate Summary                       │
    └──────────────────────────────────────────────────────┘
    generate_comprehensive_analysis_summary(...)
            ↓
        analysis_summary = {
            overview: {...},
            influencer_breakdown: {...},
            pain_point_analysis: {
                urgent_pain_points: [...]
            },
            community_insights: {...},
            key_insights: [...]
        }
            ↓
        Campaign.metadata['analysis_summary'] = analysis_summary
        Campaign.save()
            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: RESPONSE TO FRONTEND                                    │
└─────────────────────────────────────────────────────────────────┘
    Return Response:
    {
        brand_id, brand_name,
        analysis_status: 'completed',
        data_collected: {...},
        enhanced_analysis: {...}
    }
            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: FRONTEND DISPLAY                                        │
└─────────────────────────────────────────────────────────────────┘
    Dashboard.tsx receives response
            ↓
    Triggers: fetchAnalysisSummary()
            ↓
    GET /api/v1/brands/{id}/analysis-summary/
            ↓
    Receives: analysis_summary
            ↓
    Renders:
    - AI-Powered Key Insights (6 cards)
    - Urgent Pain Points table (5 rows)
    - Influencer Breakdown (3 KPI cards)
    - Top Communities grid (4 items)
```

---

## Data Models & Storage

### Database Tables

**Brand**
```sql
- id (UUID)
- name
- description
- keywords (JSON)
- sources (JSON)
- is_active
```

**Campaign**
```sql
- id (UUID)
- brand_id (FK)
- name
- status (active/paused/completed)
- metadata (JSON)  ← Stores analysis_summary
- created_at
```

**Community**
```sql
- id (UUID)
- name
- platform (reddit/discord/forum)
- url
- member_count
- echo_score
- sentiment_score
```

**Thread**
```sql
- id (UUID)
- brand_id (FK)
- campaign_id (FK)
- community_id (FK)
- title
- content
- author_username
- upvotes, downvotes
- comment_count
- sentiment_score
- analyzed_at
```

**PainPoint**
```sql
- id (UUID)
- campaign_id (FK)
- keyword
- description
- frequency
- severity
- sentiment
- created_at
- threads (M2M)  ← Links to threads
```

**Influencer**
```sql
- id (UUID)
- brand_id (FK)
- campaign_id (FK)
- username
- platform
- total_posts
- total_karma
- reach_score (0-100)
- authority_score (0-100)
- advocacy_score (0-100)
- relevance_score (0-100)
- influence_score (0-100)
- sentiment_towards_brand
- communities (JSON)
- sample_thread_ids (JSON)
```

---

## Error Handling & Retry Logic

### Orchestrator Error Handling

**Location**: `orchestrator.py`

**Retry Mechanism**:
```python
workflow.add_node("scout_content", with_retry(scout_node))
workflow.add_node("clean_content", with_retry(cleaner_node))
workflow.add_node("analyze_content", with_retry(analyst_node))
```

**Error Flow**:
```
Node execution fails
        │
        ▼
error_handler node
        │
        ├──▶ Assess error type
        │    - Transient (retry)
        │    - Fatal (abort)
        │    - External (escalate)
        │
        └──▶ Decision:
             - "retry": Back to route_workflow
             - "abort": Jump to finalize_workflow
             - "escalate": Log & finalize_workflow
```

### Celery Task Retry

**Configuration**:
```python
@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def scout_reddit_task(self, ...):
    try:
        # Task logic
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)
```

---

## Performance & Monitoring

### Metrics Tracked

**Workflow Level**:
- Total execution time
- Time per node
- Success/failure rates
- Retry counts

**Agent Level**:
- Scout: Items collected, API calls, scrape time
- Cleaner: Items processed, PII masked, spam filtered
- Analyst: Insights generated, influencers found, confidence scores

**Cost Tracking**:
- LLM tokens used (GPT-4)
- API calls (Reddit, etc.)
- Total USD cost per workflow

**Storage**:
- Database: DashboardMetrics table
- External: LangSmith traces
- Logs: Structured logging

---

## API Endpoints Summary

### Analysis Control
- `POST /api/v1/brands/{id}/analysis/` - Start/pause analysis
- `GET /api/v1/brands/{id}/analysis-summary/` - Get analysis results

### Scout Triggers
- `POST /api/v1/scout/analyze/` - Direct scout trigger
- `POST /api/v1/tasks/scout/` - Manual scout task

### Data Retrieval
- `GET /api/v1/brands/{id}/influencers/` - Get influencers
- `GET /api/v1/brands/{id}/scout-results/` - Get scout data
- `GET /api/v1/communities/` - Get communities
- `GET /api/v1/pain-points/` - Get pain points
- `GET /api/v1/threads/` - Get threads

### Monitoring
- `GET /api/v1/monitoring/dashboard/` - Monitoring overview
- `GET /api/v1/monitoring/workflows/metrics/` - Workflow metrics
- `GET /api/v1/monitoring/agents/health/` - Agent health

---

## Security & Compliance

### PII Handling
- **Detection**: Regex + LLM validation
- **Masking**: Replace with generic placeholders
- **Storage**: No PII in database (cleaned content only)
- **Compliance**: GDPR, CCPA compliant

### Data Retention
- **Threads**: 30 days (configurable)
- **Campaigns**: Archived after completion
- **Audit Logs**: 90 days
- **Metrics**: 1 year

### Rate Limiting
- **Reddit API**: 60 requests/minute
- **Web Scraping**: Respectful delays (2-5s)
- **LLM Calls**: Budget-aware throttling

---

## Future Enhancements

### Planned Features
1. **Real-time WebSocket Updates** - Live progress in dashboard
2. **Parallel Processing** - Multi-brand concurrent analysis
3. **Advanced Scheduling** - Custom cron expressions
4. **Alert System** - Email/Slack notifications for urgent pain points
5. **Export Features** - PDF/CSV reports
6. **Historical Trending** - Track influencer score changes over time
7. **Network Analysis** - Visualize influencer relationships
8. **Predictive Analytics** - ML-based pain point forecasting

---

## Quick Reference

### Start Analysis
```bash
curl -X POST http://localhost:8000/api/v1/brands/{brand_id}/analysis/ \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'
```

### Get Results
```bash
curl http://localhost:8000/api/v1/brands/{brand_id}/analysis-summary/
```

### Manual Scout
```bash
curl -X POST http://localhost:8000/api/v1/scout/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Your Brand",
    "keywords": ["keyword1", "keyword2"]
  }'
```

### Trigger Background Task
```bash
curl -X POST http://localhost:8000/api/v1/tasks/scout/ \
  -H "Content-Type: application/json" \
  -d '{"campaign_id": 123}'
```

---

**Last Updated**: October 22, 2025
**Version**: 1.0
**Status**: Production Ready ✅
