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
│  3. Chat Interface (RAG Chatbot)                                     │
│  4. Manual Triggers (Admin)                                          │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR (LangGraph)                        │
│  - Workflow coordination                                             │
│  - Conditional routing (task-based / chat-based)                     │
│  - Error handling & retry                                            │
│  - State management (MemorySaver)                                    │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                ┌────────────────┼────────────────┬────────────────┐
                ▼                ▼                ▼                ▼
         ┌──────────┐     ┌──────────┐    ┌──────────┐    ┌──────────┐
         │  SCOUT   │────▶│ CLEANER  │───▶│ ANALYST  │    │ CHATBOT  │
         │  AGENT   │     │  AGENT   │    │  AGENT   │    │  AGENT   │
         │          │     │          │    │          │    │  (RAG)   │
         └──────────┘     └──────────┘    └──────────┘    └──────────┘
         │ Tavily    │ PII/Spam     │ Influencer    │ Vector      │
         │ Search    │ Filtering    │ Scoring       │ Search      │
         │ 6mo/3mo   │ Toxicity     │ Insights      │ + LLM       │
         └──────────┘     └──────────┘    └──────────┘    └──────────┘
                │                │              │                │
                │                │              │                │
                ▼                ▼              ▼                ▼
         ┌────────────────────────────────────────────────────────────┐
         │               MONITORING AGENT                             │
         │  - Performance tracking (LangSmith)                        │
         │  - Compliance logging (Guardrails)                         │
         │  - Cost monitoring (Token tracking)                        │
         │  - RAG interaction tracking                                │
         └────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                         ┌───────────────────┐
                         │   DATABASE        │
                         │   (PostgreSQL     │
                         │    + pgvector)    │
                         │                   │
                         │ - Communities     │
                         │ - Threads         │
                         │ - Pain Points     │
                         │ - Influencers     │
                         │ - Insights        │
                         │ - Embeddings      │
                         └───────────────────┘
```

**Agent Routing Logic**:

```
User Request
    │
    ├──▶ IF task_type == "brand_analysis"
    │         └──▶ Scout → Cleaner → Analyst → Monitoring
    │
    ├──▶ IF task_type == "chat_query"
    │         └──▶ Chatbot (RAG) → Monitoring
    │
    ├──▶ IF task_type == "campaign_analysis"
    │         └──▶ Scout → Cleaner → Analyst → Monitoring
    │
    └──▶ IF task_type == "monitoring"
              └──▶ Monitoring Agent (health check)
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
- route_workflow       # Determine routing strategy (task-based/chat-based)
- scout_content        # Data collection (Tavily Search, 6mo Brand/3mo Custom)
- clean_content        # Data cleaning (PII, spam, toxicity)
- analyze_content      # Analysis & insights (influencer scoring)
- chatbot_node         # RAG/Chat queries (vector search + LLM)
- monitoring_agent     # Performance monitoring
- parallel_orchestrator # Parallel processing
- workflow_monitor     # Workflow health checks
- error_handler        # Error recovery
- finalize_workflow    # Completion & cleanup
```

**Routing Logic**:
```python
def route_workflow(state: EchoChamberAnalystState) -> str:
    """
    Conditional routing based on task type.
    
    Routes:
    1. "brand_analysis" → scout_content
    2. "chat_query" → chatbot_node
    3. "campaign_analysis" → scout_content
    4. "monitoring" → monitoring_agent
    """
    
    task_type = state.get("task_type", "brand_analysis")
    
    if task_type == "chat_query":
        # User query through chat interface
        return "chat_query"  # → chatbot_node
    
    elif task_type in ["brand_analysis", "campaign_analysis"]:
        # Data collection and analysis pipeline
        return "scout_content"  # → scout_content → cleaner → analyst
    
    elif task_type == "monitoring":
        # Health check and metrics
        return "monitoring"  # → monitoring_agent
    
    else:
        # Default to brand analysis
        return "scout_content"
```

**Edge Configuration**:
```python
# Conditional routing from start
workflow.add_conditional_edges(
    "start",
    route_workflow,
    {
        "scout_content": "scout_content",
        "chat_query": "chatbot_node",
        "monitoring": "monitoring_agent"
    }
)

# Sequential pipeline for data analysis
workflow.add_edge("scout_content", "clean_content")
workflow.add_edge("clean_content", "analyze_content")
workflow.add_edge("analyze_content", "monitoring_agent")

# Chat workflow directly to monitoring
workflow.add_edge("chatbot_node", "monitoring_agent")

# All paths converge at monitoring, then finalize
workflow.add_edge("monitoring_agent", "finalize_workflow")
workflow.add_edge("finalize_workflow", END)
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

**Purpose**: Real-time data collection from multiple platforms with intelligent community selection

**Data Sources**:
- Reddit (via PRAW API)
- Forums (web scraping)
- Review sites
- Social media platforms

**Key Optimizations** (Phase 5+):
- **Tavily Search API**: Primary data source replacing web scraping (LLM-driven queries)
- **6-Month Brand Analytics**: Comprehensive historical data for automatic campaigns
- **3-Month Custom Campaigns**: Focused strategic snapshot for objective-driven analysis
- **Token Efficiency**: 90% reduction in LLM token usage via optimized insight generation
- **Resilient Data Saving**: Individual item error handling with comprehensive statistics

**Flow**:
```
User Trigger/Schedule
        │
        ▼
  scout_node()
        │
        ├──▶ STEP 1: LLM-Driven Keyword Deduplication
        │         │
        │         ├──▶ _normalize_and_deduplicate_keywords()
        │         │    - Semantic grouping of pain point keywords
        │         │    - Reduces redundant Tavily searches
        │         │    - Example: ["sizing issues", "size problems"] → "sizing and fit issues"
        │         │
        │         └──▶ Optimized keyword list for search
        │
        ├──▶ STEP 2: Monthly Tavily Search (6 or 3 months)
        │         │
        │         ├──▶ collect_real_brand_data()
        │         │    - Tavily Search API (NOT web scraping)
        │         │    - Brand Analytics: 6 completed months
        │         │    - Custom Campaigns: 3 completed months
        │         │    - Monthly iteration for temporal accuracy
        │         │
        │         ├──▶ For each month:
        │         │    - search_month_with_tavily_and_llm()
        │         │    - LLM generates search queries (brand + keywords)
        │         │    - Tavily executes searches
        │         │    - extract_threads_with_llm() from results
        │         │
        │         ├──▶ Returns collected_data:
        │         │    - communities (discovered via Tavily)
        │         │    - threads (6mo Brand / 3mo Custom)
        │         │    - pain_points (extracted)
        │         │    - brand_mentions
        │
        ├──▶ STEP 3: Source Discovery & Storage
        │         │
        │         ├──▶ Discover new Reddit communities and forums
        │         ├──▶ Store in Source model for future use
        │         └──▶ Enable learning and improved targeting
        │
        ├──▶ STEP 4: Resilient Data Storage
        │         │
        │         │    │
        │         │    ├──▶ resilient_bulk_save(communities)
        │         │    │    - Individual save per community
        │         │    │    - Continue on errors
        │         │    │    - Case-insensitive deduplication
        │         │    │
        │         │    ├──▶ resilient_bulk_save(pain_points)
        │         │    │    - Monthly separation (month_year field)
        │         │    │    - Community linking
        │         │    │    - Conflict resolution
        │         │    │
        │         │    ├──▶ resilient_bulk_save(threads)
        │         │    │    - Thread URL storage
        │         │    │    - Author tracking
        │         │    │    - Week tagging (month_year)
        │         │    │
        │         │    ├──▶ _extract_and_store_influencers()
        │         │    │    - 4-component scoring
        │         │    │    - Reach, Authority, Advocacy, Relevance
        │         │    │
        │         │    └──▶ Save Results Tracking
        │         │         - total, succeeded, failed per type
        │         │         - Error logging for retry
        │         │         - Success rate calculation
        │
        ├──▶ STEP 4: Optimized Insight Generation
        │         │
        │         ├──▶ _generate_and_store_campaign_insights()
        │         │    │
        │         │    ├──▶ IF campaign_type == 'custom':
        │         │    │    - Strategic report (objective-focused)
        │         │    │    - generate_strategic_campaign_report()
        │         │    │    - Aligned with campaign goals
        │         │    │
        │         │    └──▶ ELSE (Brand Analytics):
        │         │         - Optimized insight generation (90% token savings)
        │         │         - Pre-aggregate data (no LLM)
        │         │         - Single LLM call with compact summary
        │         │         - generate_campaign_ai_insights()
        │         │         - 6 simple insights (not strategic report)
        │
        ├──▶ STEP 5: Calculate Echo Scores
        │         │
        │         └──▶ recalculate_all_community_scores()
        │              - Post-data echo score calculation
        │              - Based on thread counts & pain points
        │
        ▼
   Database Storage Complete:
   - Communities (discovered, with echo scores)
   - Threads (6mo Brand / 3mo Custom, with URLs)
   - PainPoints (monthly aggregation)
   - Influencers (4-component scores)
   - Insights (6 AI insights OR strategic report)
        │
        ▼
   Pass to CLEANER (if needed)
```

**Input**:
- `EchoChamberAnalystState` with campaign context
- Brand name, keywords, sources
- Scout configuration (target_communities, collection_months)

**Output**:
- `state.raw_content` - List of ContentItem objects
- **Stored in database**:
  - Communities (discovered via Tavily) with echo scores
  - Threads (6 months for Brand Analytics, 3 months for Custom) with URLs and month tags
  - PainPoints (monthly aggregation with community links)
  - Influencers (4-component scoring model)
  - Insights (6 AI insights OR strategic report based on campaign type)
- **Metrics**: 
  - collection_time, items_collected
  - save_results (total/succeeded/failed per type)
  - token_usage (90% optimized for Brand Analytics)

**Data Collection Strategy** (Tavily Search + LLM Analysis):

1. **Tavily Search Integration** (primary data source):
   ```python
   # Scout now uses Tavily Search API (NOT web scraping)
   from tavily import TavilyClient
   
   tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
   
   # Search per month with LLM-generated queries
   for month_info in months:  # Last 6 or 3 months
       # LLM generates search queries based on pain points + brand
       search_queries = await generate_search_queries(
           brand_name=brand_name,
           keywords=pain_point_keywords,
           month=month_info['month_str']
       )
       
       # Execute Tavily search for each query
       for query in search_queries:
           response = tavily_client.search(
               query=query,
               search_depth="comprehensive",  # Brand Analytics
               max_results=5,
               include_domains=["reddit.com"]
           )
           # Extract threads from Tavily results using LLM
           threads = await extract_threads_with_llm(response)
   ```

2. **Collection Periods** (campaign-specific):
   ```python
   # Brand Analytics (automatic monitoring): 6 MONTHS
   config_brand_analytics = {
       'collection_months': 6,        # Last 6 completed months
       'search_depth': 'comprehensive',
       'use_llm_discovery': True
   }
   
   # Custom Campaigns (strategic focus): 3 MONTHS
   config_custom_campaign = {
       'collection_months': 3,        # Last 3 completed months
       'search_depth': 'focused',
       'use_llm_discovery': True
   }
   
   # Time window calculation (past complete months only)
   today = datetime.now()
   start_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
   months = []
   for i in range(num_months):
       month_start = start_month - relativedelta(months=i)
       month_end = month_start + relativedelta(months=1) - timedelta(days=1)
       months.append({'start': month_start, 'end': month_end})
   ```

3. **LLM-Driven Search Strategy**:
   ```python
   # Function: search_month_with_tavily_and_llm()
   # For each month:
   #   1. Normalize pain point keywords (LLM semantic deduplication)
   #   2. Generate 3-5 search queries (LLM combines brand + keywords)
   #   3. Execute Tavily search per query
   #   4. Extract threads from results (LLM analyzes content)
   #   5. Aggregate results per month
   
   # Example LLM prompt for keyword deduplication:
   normalized_keywords = await llm_normalize_keywords([
       "sizing issues", "size problems", "fit concerns"
   ])
   # Result: ["sizing and fit issues"]  # Semantically grouped
   ```

4. **Source Discovery & Storage**:
   ```python
   # As Scout searches, it discovers new sources (Reddit communities, forums)
   # These are stored in the Source model for future use
   
   discovered_sources = []
   for thread in threads_found:
       source_name = extract_source_name(thread['url'])  # e.g., "r/Nike"
       source, created = Source.objects.get_or_create(
           name=source_name,
           defaults={
               'platform': 'reddit',
               'category': 'community',
               'is_default': False,
               'description': f'Discovered from {brand.name} analysis'
           }
       )
       discovered_sources.append(source)
   ```

5. **Resilient Saving** (individual item handling):
   ```python
   save_results = resilient_bulk_save(
       items=communities_data,
       save_function=save_community,
       item_type="Community",
       get_item_id=lambda x: x.get('name', 'unknown')
   )
   # Returns SaveResult:
   # {
   #   total: discovered_count, succeeded: X, failed: Y,
   #   created: N, updated: M,
   #   success_rate: X%, errors: []
   # }
   ```

6. **Optimized Insights** (90% token reduction):
   ```python
   # For Brand Analytics (automatic campaign):
   # Pre-aggregate data (NO LLM, cheap)
   data_summary = {
       'total_threads': len(threads),
       'top_pain_points': sorted(pain_points)[:5],  # Already extracted
       'sentiment_breakdown': {...},  # Already calculated
       'top_communities': sorted(communities)[:3],  # By echo score
       'sample_threads': sorted(threads)[:3]  # High-value only
   }
   
   # Single LLM call with compact summary (90% token savings)
   campaign_insights = await generate_campaign_ai_insights(
       campaign, brand, {'data_summary': data_summary}
   )
   ```

**Triggered By**:
1. **User Action**: `POST /api/v1/brands/{id}/analysis/` (action: 'start')
2. **Direct API**: `POST /api/v1/scout/analyze/`
3. **Scheduled Celery Tasks**:
   - `scout_reddit_task` - General periodic task, 6 months
   - `scout_brand_analytics_task` - Brand Analytics monitoring, 6 months, comprehensive depth
   - `scout_custom_campaign_task` - Custom campaigns, 3 months, focused depth
4. **Manual**: `POST /api/v1/tasks/scout/`

**Triggers Next**:
- Automatically passes to **CLEANER AGENT** via orchestrator (if state-based)
- OR directly stores and generates insights (for API-triggered runs)

---

### 3. DATA CLEANER AGENT

**Location**: `backend/agents/nodes.py` - `cleaner_node()`

**Purpose**: Advanced content validation, PII removal, spam filtering, compliance tracking

**Enhanced Capabilities** (Phase 5):
- **Advanced PII Detection**: 5 PII types (emails, phones, SSNs, credit cards, addresses)
- **Multi-layer Spam Detection**: Pattern-based + score-based filtering
- **Toxicity Filtering**: Content safety with toxicity scoring (0-1)
- **Enhanced Sentiment Analysis**: Context-aware with positive/negative word detection
- **Entity Extraction**: Keywords and brand entity recognition
- **Duplicate Detection**: Content similarity comparison
- **Compliance Tracking**: All filtering operations logged for audit
- **Dashboard Optimization**: Data sanitization for display

**Flow**:
```
SCOUT output (raw_content)
        │
        ▼
  cleaner_node()
        │
        ├──▶ STEP 1: Enhanced PII Detection & Masking
        │         │
        │         ├──▶ Pattern Matching:
        │         │    - Email: user@example.com → [EMAIL_REMOVED]
        │         │    - Phone: 555-123-4567 → [PHONE_REMOVED]
        │         │    - SSN: 123-45-6789 → [SSN_REMOVED]
        │         │    - Credit Card: 1234-5678-9012-3456 → [CREDIT_CARD_REMOVED]
        │         │    - Address: 123 Main Street → [ADDRESS_REMOVED]
        │         │
        │         ├──▶ GDPR/CCPA Compliance
        │         └──▶ Track: cleaning_stats["pii_instances_removed"]
        │
        ├──▶ STEP 2: Multi-layer Spam & Bot Filtering
        │         │
        │         ├──▶ Spam Indicators:
        │         │    - "buy now", "click here", "limited time"
        │         │    - "discount", "sale", "promotion"
        │         │    - "subscribe", "follow", "like and share"
        │         │    - "bitcoin", "crypto", "investment"
        │         │
        │         ├──▶ Spam Score Calculation:
        │         │    - Count matching indicators
        │         │    - Threshold: spam_score >= 2
        │         │
        │         ├──▶ Compliance Logging:
        │         │    global_monitor.compliance_tracker.log_content_filtering(
        │         │        content_id, "spam", spam_score
        │         │    )
        │         │
        │         └──▶ Track: cleaning_stats["spam_filtered"]
        │
        ├──▶ STEP 3: Toxicity & Harmful Content Detection
        │         │
        │         ├──▶ Toxic Patterns:
        │         │    - Hate speech, insults, threats
        │         │    - Racist, sexist, homophobic language
        │         │    - Violent or harmful content
        │         │
        │         ├──▶ Toxicity Score (0-1):
        │         │    - Pattern match count × 0.3
        │         │    - Capped at 1.0
        │         │    - Filter if > 0.8
        │         │
        │         ├──▶ Compliance Logging:
        │         │    global_monitor.compliance_tracker.log_content_filtering(
        │         │        content_id, "toxicity", toxicity_score
        │         │    )
        │         │
        │         └──▶ Track: cleaning_stats["toxic_content_filtered"]
        │
        ├──▶ STEP 4: Enhanced Sentiment Analysis
        │         │
        │         ├──▶ Word-based Analysis:
        │         │    - Positive words: great, awesome, excellent, love
        │         │    - Negative words: terrible, awful, hate, horrible
        │         │
        │         ├──▶ Sentiment Score (-1 to +1):
        │         │    sentiment = (positive_count - negative_count) / 
        │         │                max(positive_count + negative_count, 1)
        │         │
        │         └──▶ Store: content_item.sentiment_score
        │
        ├──▶ STEP 5: Entity & Keyword Extraction
        │         │
        │         ├──▶ Keywords (domain-specific):
        │         │    - Product terms: shirt, pants, shoes, fabric
        │         │    - Quality terms: comfort, durability, breathable
        │         │    - Limit: Top 10 keywords
        │         │
        │         ├──▶ Entities (brands, products):
        │         │    - Pattern-based extraction
        │         │    - Brand names: Nike, Adidas, Uniqlo, etc.
        │         │
        │         └──▶ Store: content_item.keywords, content_item.entities
        │
        ├──▶ STEP 6: Deduplication
        │         │
        │         ├──▶ Similarity Detection:
        │         │    - Content length comparison
        │         │    - First 100 characters match
        │         │
        │         ├──▶ Remove duplicates
        │         └──▶ Track: cleaning_stats["duplicates_removed"]
        │
        ├──▶ STEP 7: Content Quality Scoring
        │         │
        │         ├──▶ Quality Factors:
        │         │    - Length score (prefer 500+ chars)
        │         │    - Sentence score (prefer 3+ sentences)
        │         │    - Caps usage (penalize excessive caps)
        │         │    - Punctuation (penalize excessive !!!)
        │         │
        │         ├──▶ Quality Score (0-1)
        │         └──▶ Store: cleaned_data["quality_score"]
        │
        ▼
  state.cleaned_content
        │
        ├──▶ Comprehensive Audit Log:
        │    - Action: "enhanced_content_cleaning"
        │    - Raw count, cleaned count, filtered count
        │    - Cleaning stats (PII, spam, toxic, duplicates)
        │    - Capabilities: 7 enhanced capabilities
        │
        ▼
   Pass to ANALYST
```

**Input**:
- `state.raw_content` - Raw data from Scout (ContentItem list)
- Cleaning configuration (PII patterns, spam indicators, toxicity patterns)
- Compliance rules (GDPR, CCPA)

**Output**:
- `state.cleaned_content` - Validated ContentItem list with:
  - `is_cleaned = True`
  - `sentiment_score` (-1 to +1)
  - `toxicity_score` (0 to 1)
  - `keywords` (list of extracted keywords)
  - `entities` (list of extracted entities)
  - `language` (detected language, default "en")
- **Cleaning Statistics**:
  ```python
  cleaning_stats = {
      "pii_instances_removed": 12,
      "spam_filtered": 8,
      "toxic_content_filtered": 3,
      "duplicates_removed": 5,
      "total_processed": 150,
      "compliance_violations": []  # Errors logged
  }
  ```
- **Quality scores** per item (length, sentences, readability)

**Processing Strategy**:

1. **PII Detection** (_enhanced_clean_content):
   ```python
   pii_patterns = {
       "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
       "phone": r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
       "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
       "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
       "address": r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd)\b'
   }
   
   for pii_type, pattern in pii_patterns.items():
       if re.search(pattern, content):
           has_pii = True
           cleaned_content = re.sub(pattern, f'[{pii_type.upper()}_REMOVED]', content)
   ```

2. **Spam Filtering** (multi-indicator):
   ```python
   spam_indicators = [
       r'\b(?:buy now|click here|limited time|act now)\b',
       r'\b(?:discount|sale|offer|deal|promotion)\b',
       r'\b(?:subscribe|follow|like and share)\b',
       r'\b(?:bitcoin|crypto|investment|profit)\b'
   ]
   
   spam_score = sum(1 for indicator in spam_indicators 
                    if re.search(indicator, content, re.IGNORECASE))
   
   is_spam = spam_score >= 2  # Threshold: 2+ indicators
   
   if is_spam:
       cleaning_stats["spam_filtered"] += 1
       global_monitor.compliance_tracker.log_content_filtering(
           content_id, "spam", spam_score / len(spam_indicators)
       )
       continue  # Skip this content
   ```

3. **Toxicity Detection**:
   ```python
   toxic_patterns = [
       r'\b(?:hate|stupid|idiot|moron|loser)\b',
       r'\b(?:kill yourself|die|death)\b',
       r'\b(?:racist|sexist|homophobic)\b'
   ]
   
   toxicity_score = 0
   for pattern in toxic_patterns:
       matches = len(re.findall(pattern, content, re.IGNORECASE))
       toxicity_score += matches * 0.3
   
   toxicity_score = min(toxicity_score, 1.0)
   
   if toxicity_score > 0.8:  # High toxicity threshold
       cleaning_stats["toxic_content_filtered"] += 1
       global_monitor.compliance_tracker.log_content_filtering(
           content_id, "toxicity", toxicity_score
       )
       continue  # Filter out
   ```

4. **Sentiment Analysis** (enhanced):
   ```python
   positive_words = ['great', 'awesome', 'excellent', 'love', 'perfect', 'amazing']
   negative_words = ['terrible', 'awful', 'hate', 'horrible', 'worst', 'bad']
   
   content_lower = content.lower()
   positive_count = sum(1 for word in positive_words if word in content_lower)
   negative_count = sum(1 for word in negative_words if word in content_lower)
   
   sentiment_score = (positive_count - negative_count) / 
                     max(positive_count + negative_count, 1)
   sentiment_score = max(-1.0, min(1.0, sentiment_score))  # Clamp [-1, 1]
   
   content_item.sentiment_score = sentiment_score
   ```

5. **Duplicate Detection** (_is_duplicate_content):
   ```python
   for existing_item in cleaned_items:
       # Simple similarity: length + first 100 chars
       if (abs(len(content_item.content) - len(existing_item.content)) < 10 and
           content_item.content[:100] == existing_item.content[:100]):
           cleaning_stats["duplicates_removed"] += 1
           return True  # Is duplicate
   return False
   ```

**Compliance Tracking**:

All filtering operations are logged via global_monitor:

```python
# PII detected
global_monitor.compliance_tracker.log_content_filtering(
    content_id="thread_abc123",
    reason="pii_detected",
    confidence=1.0
)

# Spam filtered
global_monitor.compliance_tracker.log_content_filtering(
    content_id="thread_xyz789",
    reason="spam",
    confidence=0.9
)

# Toxic content
global_monitor.compliance_tracker.log_content_filtering(
    content_id="thread_def456",
    reason="toxicity",
    confidence=0.85
)
```

**Audit Logging**:

Comprehensive audit log created at end of cleaning:

```python
audit_tool = LANGGRAPH_TOOLS["create_audit_log"]
await audit_tool._arun(
    action_type="enhanced_content_cleaning",
    action_description=f"Enhanced Cleaner processed {len(raw_content)} items, "
                      f"cleaned {len(cleaned_items)}",
    agent_name="enhanced_cleaner_node",
    metadata={
        "raw_count": len(raw_content),
        "cleaned_count": len(cleaned_items),
        "filtered_count": len(raw_content) - len(cleaned_items),
        "cleaning_stats": cleaning_stats,
        "capabilities": [
            "pii_detection_removal",
            "spam_filtering",
            "data_validation",
            "content_sanitization",
            "duplicate_removal",
            "sentiment_normalization",
            "compliance_checking"
        ]
    }
)
```

**Triggered By**:
- Automatically by **ORCHESTRATOR** after Scout completes
- Edge: `scout_content → clean_content`

**Triggers Next**:
- Automatically passes to **ANALYST AGENT**

**Performance Notes**:
- Batch processing: 5 items per batch (adjustable)
- LLM-assisted validation: Optional, used for complex cases
- Rule-based filtering: Primary method for speed
- Token cost: ~0.003 USD per item (enhanced processing)
- Average processing time: ~100ms per item

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
        ├──▶ Unified Content & Influencer Analysis
        │    - Single module for all analysis (not separate modules)
        │    - LLM: gpt-4, temperature=0.3, max_tokens=3000
        │    - Functions: analyze_influencers, aggregate_metrics, calculate_scores
        │
        ├──▶ analyze_influencers_for_threads()
        │         │
        │         ├──▶ aggregate_user_metrics_from_threads()
        │         │    - Aggregate posts, upvotes, unique threads per user
        │         │    - Track community participation
        │         │    - Calculate engagement rates
        │         │
        │         ├──▶ calculate_influence_scores()
        │         │    ├─▶ calculate_reach_score() [30% weight]
        │         │    │   - Post volume + Total engagement + Community diversity
        │         │    │   - Formula: (post_count × 0.4) + (engagement × 0.4) + (communities × 0.2)
        │         │    │
        │         │    ├─▶ calculate_authority_score() [30% weight]
        │         │    │   - Consistency + Quality + Engagement ratio
        │         │    │   - Formula: (consistency × 0.4) + (quality × 0.3) + (eng_ratio × 0.3)
        │         │    │
        │         │    ├─▶ calculate_advocacy_score() [20% weight]
        │         │    │   - Brand mention rate + Sentiment score
        │         │    │   - Formula: (mention_rate × 0.6) + (sentiment × 0.4)
        │         │    │
        │         │    └─▶ calculate_relevance_score() [20% weight]
        │         │        - Mention frequency + Volume + Community relevance
        │         │        - Formula: (frequency × 0.4) + (volume × 0.3) + (comm_rel × 0.3)
        │         │
        │         ▼
        │    Influencer List with 4-component scores
        │
        ├──▶ save_influencers_to_db()
        │         │
        │         ▼
        │    Database: Influencer records with scores
        │
        ├──▶ link_pain_points_to_influencers()
        │         │
        │         ├──▶ Cross-reference threads with influencers
        │         ├──▶ Calculate total reach per pain point
        │         ├──▶ Sentiment breakdown (positive/negative/neutral)
        │         ├──▶ Urgency scoring (0-10 based on growth + sentiment)
        │         └──▶ Generate actionable recommendations
        │         │
        │         ▼
        │    Pain Point Analysis with Influencer Impact
        │
        ├──▶ generate_comprehensive_analysis_summary()
        │         │
        │         ├──▶ Overview metrics (threads, communities, pain points)
        │         ├──▶ Influencer breakdown (top 5 by advocacy score)
        │         ├──▶ Urgent pain points (sorted by urgency + reach)
        │         ├──▶ Community insights (echo scores + key influencers)
        │         └──▶ Key actionable insights (LLM-generated)
        │         │
        │         ▼
        │    Campaign.metadata['analysis_summary']
        │
        └──▶ generate_brand_analytics_ai_insights() [Dashboard only]
                  │
                  ├──▶ Uses OpenAI o1-mini (reasoning model) + fallback to gpt-4
                  ├──▶ Analyzes all dashboard data:
                  │    - KPIs (active campaigns, high-echo communities, new pain points)
                  │    - Community Watchlist (top communities by echo score)
                  │    - Pain Point Trends (6-month time series data)
                  │    - Influencer Pulse (top influencers by advocacy)
                  │    - Community × Pain Point Matrix (bubble chart data)
                  │    - Total Mention Volume Trend (6-month aggregation)
                  │
                  ├──▶ Generates 6 strategic insights covering:
                  │    1. Brand health assessment (echo scores + positivity)
                  │    2. Community engagement opportunities (matrix analysis)
                  │    3. Pain point analysis (time series trends)
                  │    4. Influencer strategy (partnership opportunities)
                  │    5. Trend analysis (6-month patterns + seasonality)
                  │    6. Strategic recommendations (immediate actions)
                  │
                  └──▶ Returns: List[str] with 6 insights (1-2 sentences each)
                       │
                       ▼
                  Displayed in Dashboard "AI-Powered Key Insights" section
```

**Input**:
- `state.cleaned_content` - Validated content
- Campaign context (brand, keywords, goals, campaign_type)
- Analysis configuration
- Dashboard data (for Brand Analytics AI insights):
  - KPIs (active_campaigns, high_echo_communities, new_pain_points, positivity_ratio)
  - Community Watchlist (communities with echo scores, key influencers)
  - Pain Point Trends (6-month time series data)
  - Influencer Pulse (top influencers by advocacy score)
  - Community × Pain Point Matrix (bubble chart data)
  - Total Mention Volume Trend (6-month aggregated data)

**Output**:
- `state.insights` - List of generated insights (6 insights for dashboard, OR strategic report)
- `state.influencers` - Detected influencer profiles with 4-component scores
- Database: 
  - Influencer records (handle, platform, reach, authority, advocacy, relevance)
  - Linked pain points (pain_point → influencers → reach + sentiment)
- Campaign.metadata['analysis_summary'] - Comprehensive summary:
  ```json
  {
    "overview": {
      "total_threads_analyzed": 250,
      "communities_monitored": 15,
      "pain_points_identified": 45,
      "influencers_detected": 50
    },
    "influencer_breakdown": [
      {"handle": "@user1", "advocacy_score": 8.5, "reach": 50000},
      ...
    ],
    "urgent_pain_points": [
      {
        "keyword": "sizing issues",
        "urgency": 8.7,
        "total_reach": 150000,
        "sentiment": -0.45,
        "recommendation": "Address in next product release"
      },
      ...
    ],
    "community_insights": [...],
    "key_actionable_insights": [...]
  }
  ```

**LLM Configuration**:
- **Analyst Module**: `gpt-4`, temperature=0.3 (slightly creative), max_tokens=3000
- **Dashboard Insights**: `o1-mini` (OpenAI reasoning model) with fallback to `gpt-4`
  - Model comparison: o3-mini for deep reasoning, gpt-4 for balanced analysis
  - Temperature: 0.7 (gpt-4 fallback), max_tokens=800
  - Prompt: 6 strategic insights covering brand health, community engagement, pain points, influencers, trends, recommendations

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

### 4. Chat Query (RAG Chatbot)

**Endpoint**: `POST /api/v1/chat/`

**Request**:
```json
{
  "query": "What are the main pain points for Nike?",
  "campaign_id": "uuid-optional",
  "conversation_history": [
    {"role": "user", "content": "Tell me about Nike campaigns"},
    {"role": "assistant", "content": "Here's what I found..."}
  ]
}
```

**Flow**:
```
User types query in ChatInterface
        │
        ▼
Frontend: POST /api/v1/chat/
        │
        ▼
Backend: chat_query(request)
        │
        ├──▶ Validate query (required)
        ├──▶ Get Campaign (if campaign_id provided)
        ├──▶ Convert conversation_history to LangChain messages
        │
        ▼
workflow_orchestrator.execute_chat_workflow(
    user_query=query,
    conversation_history=messages,
    campaign_id=campaign_id
)
        │
        ├──▶ Initialize state with task_type="chat_query"
        │
        ▼
Orchestrator: route_workflow()
        │
        └──▶ Routes to "chat_query" → chatbot_node
                  │
                  ▼
            chatbot_node()  [CHATBOT AGENT]
                  │
                  ├──▶ Guardrails validation
                  ├──▶ Execute rag_tool.run()  [Pure RAG]
                  │    │
                  │    ├──▶ Intent classification (GPT-4o-mini)
                  │    ├──▶ Query rewriting with context
                  │    ├──▶ Vector search (pgvector - semantic or combined mode)
                  │    ├──▶ Context assembly from embeddings
                  │    └──▶ Response generation (GPT-4o)
                  │
                  ├──▶ Guardrails output sanitization
                  ├──▶ Update conversation_history
                  ├──▶ Store in state.rag_context
                  └──▶ Track metrics & audit
                  │
                  ▼
         Return to chat_query()
                  │
                  ▼
    Extract response from final_state.rag_context
                  │
                  ▼
         Response to Frontend
                  │
                  ▼
    ChatInterface displays answer with sources
```

**Response**:
```json
{
  "response": "Based on the collected data, Nike's main pain points are:\n1. Sizing inconsistency (45 mentions)...",
  "context_used": 8,
  "sources": [
    {
      "type": "pain_points",
      "content_preview": "Pain Point: sizing issues\nMentions: 45...",
      "similarity_score": 0.876,
      "source": "r/Nike",
      "date": "2025-01-15T10:30:00Z"
    }
  ],
  "tokens_used": 1250,
  "cost": 0.0085,
  "workflow_id": "wf_abc123",
  "compliance_tracked": true
}
```

### 5. Manual Task Triggers

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

### 1. General Scout Task (Hourly)

**Schedule**: Every hour (3600 seconds)

**Task**: `agents.tasks.scout_reddit_task`

**Configuration**:
```python
config = {
    'collection_months': 6,           # Default: 6 months
    'search_depth': 'comprehensive',
    'use_llm_discovery': True
}
```

**Flow**:
```
Celery Beat Scheduler
        │
        ▼ (Every hour)
scout_reddit_task()
        │
        ├──▶ Query active campaigns (all types)
        │
        ├──▶ For each campaign:
        │    │
        │    ├──▶ collect_real_brand_data()  [SCOUT with Tavily]
        │    │    - Uses Tavily Search API
        │    │    - Collects 6 months of data
        │    │    - LLM-driven search queries
        │    │
        │    └──▶ _store_brand_scout_data()  [SCOUT → DB]
        │         - Store threads, communities, pain points
        │         - Save discovered sources
        │
        └──▶ Return statistics
```

**Purpose**:
- Automatic data collection for all active brands
- Keeps dashboard data fresh
- No user intervention required

### 2. Brand Analytics Scout Task (Continuous)

**Schedule**: Periodic (configured per brand)

**Task**: `agents.tasks.scout_brand_analytics_task`

**Configuration**:
```python
config = {
    'collection_months': 6,           # Brand Analytics: 6 months
    'search_depth': 'comprehensive',  # Deep analysis
    'use_llm_discovery': True,
    'target_communities': discovered_sources  # From previous runs
}
```

**Flow**:
```
Celery Beat Scheduler
        │
        ▼ (Brand Analytics campaigns only)
scout_brand_analytics_task()
        │
        ├──▶ Query Brand Analytics campaigns (campaign_type='brand_analytics')
        │
        ├──▶ For each brand campaign:
        │    │
        │    ├──▶ collect_real_brand_data()  [SCOUT with Tavily]
        │    │    - 6 months historical data
        │    │    - Comprehensive search depth
        │    │    - Monthly iteration with Tavily API
        │    │
        │    ├──▶ generate_brand_analytics_ai_insights()  [ANALYST]
        │    │    - Uses OpenAI o3-mini (reasoning model)
        │    │    - Analyzes all dashboard data (KPIs, charts, time series)
        │    │    - Generates 6 strategic insights
        │    │
        │    └──▶ Store to database
        │
        └──▶ Return statistics
```

**Purpose**:
- Continuous brand monitoring (6-month rolling window)
- Dashboard "AI-Powered Key Insights" generation
- Comprehensive market intelligence

### 3. Custom Campaign Scout Task (Strategic)

**Schedule**: On-demand or scheduled per campaign

**Task**: `agents.tasks.scout_custom_campaign_task`

**Configuration**:
```python
config = {
    'collection_months': 3,           # Custom Campaigns: 3 months
    'search_depth': 'focused',        # Strategic focus
    'use_llm_discovery': True,
    'target_communities': campaign_specific_sources
}
```

**Flow**:
```
Celery Beat or Manual Trigger
        │
        ▼
scout_custom_campaign_task()
        │
        ├──▶ Query custom campaigns (campaign_type='custom')
        │
        ├──▶ For each custom campaign:
        │    │
        │    ├──▶ collect_real_brand_data()  [SCOUT with Tavily]
        │    │    - 3 months data (recent strategic snapshot)
        │    │    - Focused search depth
        │    │    - Campaign objective-driven queries
        │    │
        │    ├──▶ generate_strategic_campaign_report()  [ANALYST]
        │    │    - Executive summary
        │    │    - Strategic findings with priorities
        │    │    - Key metrics and supporting data
        │    │    - Recommended next steps
        │    │
        │    └──▶ Store to database + Generate PDF
        │
        └──▶ Return statistics
```

**Purpose**:
- Strategic campaign analysis (focused 3-month window)
- Objective-driven insights
- Exportable reports (PDF)

**Comparison Table**:

| Feature | General Task | Brand Analytics Task | Custom Campaign Task |
|---------|-------------|---------------------|---------------------|
| **Collection Period** | 6 months | 6 months | 3 months |
| **Search Depth** | Comprehensive | Comprehensive | Focused |
| **Frequency** | Hourly | Continuous | On-demand/Scheduled |
| **Campaign Type** | All active | brand_analytics | custom |
| **Output** | Database storage | Database + AI Insights | Database + Strategic Report + PDF |
| **LLM Model** | gpt-4 | o3-mini + gpt-4 fallback | gpt-4 |
| **Purpose** | General monitoring | Dashboard intelligence | Strategic planning |

### 4. Daily Cleanup Task

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

## 6. CHATBOT AGENT (Pure RAG-Powered Conversational AI)

### Overview

The Chatbot Agent provides intelligent, context-aware responses to user queries using a **pure RAG (Retrieval-Augmented Generation)** system. It uses vector embeddings search (pgvector) combined with LLM-powered response generation to answer questions about brand analytics, pain points, campaigns, and insights.

**Key Capabilities:**
- Intent classification for intelligent routing (conversational/semantic/keyword/combined)
- Pure RAG with vector embeddings search across all content types (threads, pain points, insights)
- Conversation history awareness with query rewriting
- Multiple search modes: pure semantic OR semantic + keyword (both use vector embeddings)
- Guardrails for query validation and output sanitization
- LangSmith tracing for monitoring
- Source attribution with similarity scores

### Architecture

```
User Query → Intent Classification → Pure RAG Search → Context Assembly → GPT-4 Response
     ↓              ↓                      ↓                 ↓                ↓
  Validate    Determine Type         Vector DB          Format Context   Natural Language
  Guardrails  (conversational/    (pgvector search     From Embedded    Answer with Sources
              semantic/keyword/    all content types)     Results        + Similarity Scores
              combined)           Pure RAG - All Vector
```

### Chatbot Node Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ chatbot_node(state)                                             │
└─────────────────────────────────────────────────────────────────┘
            ↓
    Extract user_query, campaign context
            ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ STEP 1: Guardrails Validation                               │
    └─────────────────────────────────────────────────────────────┘
            ↓
    guardrails.validate_query(query, user_id)
            ↓
    IF invalid → Return error response
            ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ STEP 2: Execute Pure RAG Search                             │
    └─────────────────────────────────────────────────────────────┘
            ↓
    IF LangSmith enabled:
        langsmith_tracer.trace_query(rag_tool)
    ELSE:
        rag_tool.run(query, brand_id, campaign_id, history)  # Pure RAG implementation
            ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ STEP 3: Extract Response & Sources                          │
    └─────────────────────────────────────────────────────────────┘
            ↓
    IF success:
        response_text = rag_result["answer"]  # Generated from RAG context
        sources = rag_result["sources"]       # Vector search results
        metadata = rag_result["metadata"]     # Intent, tools, execution time
        
        # Sanitize output for safety
        response_text = guardrails.sanitize_output(response_text)
    ELSE:
        response_text = "Error processing query"
        sources = []
            ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ STEP 4: Track Response Quality                              │
    └─────────────────────────────────────────────────────────────┘
            ↓
    global_monitor.track_response_quality(
        query, response, context_sources, campaign_context
    )
            ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ STEP 5: Update State                                        │
    └─────────────────────────────────────────────────────────────┘
            ↓
    Add to conversation_history:
        - HumanMessage(content=user_query)
        - AIMessage(content=response_text)
            ↓
    Store in state.rag_context:
        - response
        - sources (top 5 with similarity scores)
        - metadata (intent_type, tools_executed, execution_time)
        - search_results
            ↓
    Update metrics:
        - total_tokens_used (estimated)
        - total_cost (tool-based)
        - api_calls_made (intent + tools + response)
            ↓
    Create audit_log:
        - action_type: "chat_interaction"
        - metadata: query, intent, tools, sources_found
            ↓
    Return updated state
```

### Pure RAG Tool Implementation

**Location**: `backend/agents/rag_tool.py`

**Core Principle**: Pure RAG system using vector embeddings for all queries. No external API calls or database queries for search - everything goes through pgvector embeddings.

#### Intent Classification

```python
class IntentClassifier:
    """
    Classify user query intent using GPT-4o-mini.
    
    Intent Types:
    - conversational: Greetings, chitchat (no search needed, direct response)
    - semantic: Natural language questions (pure vector similarity search)
    - keyword: Exact keyword/phrase searches (keyword matching in vector space)
    - combined: Semantic + keyword together (default for most queries)
    
    Note: ALL search strategies use vector embeddings (Pure RAG). "Combined" means
    using semantic similarity AND keyword matching together in the same vector search,
    not mixing RAG with other approaches.
    """
    
    async def classify(query: str, conversation_history: List[Dict]) -> Dict:
        """
        Returns:
        {
            "intent_type": "conversational|semantic|keyword|combined",
            "entities": {
                "brand_name": "...",
                "campaign_name": "...",
                "time_period": "...",
                "keywords": ["...", "..."],
                "content_type": "threads|pain_points|all"
            },
            "search_strategy": "conversational|vector_search|combined_search",
            "confidence": 0.95,
            "reasoning": "..."
        }
        """
**Example Classifications:**

1. **Conversational Intent** (No RAG needed):
   - Query: "Hello, how are you?"
   - Intent: `conversational`
   - Strategy: `conversational` (no vector search)
   - Response: Pre-defined greeting

2. **Semantic Intent** (Pure vector similarity):
   - Query: "What are people saying about Nike's sustainability efforts?"
   - Intent: `semantic`
   - Strategy: `vector_search` (pure semantic similarity using pgvector)
   - Entities: `brand_name: "Nike", keywords: ["sustainability"]`
   - Search: Vector embeddings across all content types

3. **Combined Intent** (Semantic + keyword in same vector search):
   - Query: "Show me recent pain points for Yamaha motorcycles"
   - Intent: `combined`
   - Strategy: `combined_search` (semantic vectors + keyword matching together)
   - Entities: `brand_name: "Yamaha", content_type: "pain_points", time_period: "recent"`
   - Search: Vector similarity + keyword filter (both in vector space - still pure RAG)

#### Query Rewriting with Context

```python
async def run(query: str, conversation_history: List[Dict]) -> Dict:
    """
    Step 0: Rewrite query with conversation context if needed
    
    Examples:
    - History: "Tell me about Nike's campaign"
      Query: "Show me the executive summary"
      Rewritten: "Show me the executive summary for Nike's campaign"
      
    - History: "What are the main pain points for Adidas?"
      Query: "Tell me more about the pricing concerns"
      Rewritten: "Tell me more about Adidas pricing concerns pain points"
    """
    if conversation_history:
        contextualized_query = await _rewrite_with_context(query, history)
    else:
        contextualized_query = query
    
    # Use contextualized query for search
    classification = await classifier.classify(contextualized_query, history)
#### Pure RAG Search Execution

```python
# Step 1: Classify intent
classification = await classifier.classify(contextualized_query, history)

# Step 2: Execute appropriate RAG search strategy (all use vector embeddings)
if search_strategy == "conversational":
    # No RAG search needed, return greeting
    return {"answer": greeting_response, "sources": []}

elif search_strategy == "vector_search":
    # Pure semantic vector search across all content types
    # Uses pgvector <-> operator for cosine similarity
    search_results = await vector_search_tool.search_all(
        query=contextualized_query,
        brand_id=brand_id,
        campaign_id=campaign_id,
        min_similarity=0.5,  # Cosine similarity threshold
        limit_per_type=10
    )
    # Returns: threads, pain_points, insights from vector DB

else:  # combined_search (default) - still pure RAG
    # Semantic vectors + keyword matching in same vector search
    # Uses pgvector for similarity + keyword filters (both in vector space)
    search_results = await combined_search_tool.search(
        query=contextualized_query,
        brand_id=brand_id,
        campaign_id=campaign_id,
        content_type=entities.get("content_type", "all"),
        min_similarity=0.5,  # Vector similarity threshold
        limit=10
    )
    # Returns: Unified results from vector search + keyword filter (Pure RAG)
```

**Important**: This is a **Pure RAG system** - ALL searches use vector embeddings stored in PostgreSQL with pgvector. The "combined" search mode uses semantic similarity AND keyword matching together in the same vector search, but it's still pure RAG (no external API calls, no database joins outside vector space).
```

#### Context Assembly

```python
# Step 3: Format search results for LLM context
context_items = []

for item in search_results.get("results", []):
    content_type = item.get("content_type")
    
    if content_type == "pain_points":
        content = f"Pain Point: {item['keyword']}\n" \
                 f"Mentions: {item['mention_count']}\n" \
                 f"Heat Level: {item['heat_level']}\n" \
                 f"Example: {item['example_content']}"
    
    elif content_type == "insights":
        content = f"{item['title']}\n{item['description']}"
    
    elif content_type == "threads":
        content = f"{item['title']}\n{item['content']}"
    
    context_items.append({
        "type": content_type,
        "content": content,
        "similarity": item.get("similarity_score", 0),
        "metadata": {
            "id": item["id"],
            "source": item.get("source", "Unknown"),
            "date": item.get("created_at")
        }
#### Response Generation (RAG Synthesis)

```python
# Step 4: Generate natural language response using GPT-4 with RAG context
async def _generate_response(query, context_items, aggregated_data, history):
    """
    Generate response using GPT-4 with RAG context from vector search.
    
    This is the "Generation" part of RAG:
    - Retrieval: Done via vector embeddings (previous step)
    - Augmented: Context assembled from top-k vector search results
    - Generation: GPT-4 synthesizes answer from retrieved context
    
    System Prompt:
    - Be conversational and helpful
    - Synthesize information from multiple sources
    - Cite specific examples from retrieved content
    - Organize information logically
    - Only use information from retrieved RAG context
    - DO NOT make up information not in context
    """
    
    # Build RAG context from vector search results
    context = "### Relevant Content from Vector Embeddings:\n\n"
    
    for idx, item in enumerate(context_items[:10], 1):  # Top 10 from vector search
        context += f"{idx}. **{item['type']}** (Similarity: {item['similarity']:.2f})\n"
        context += f"   Source: {item['metadata']['source']}\n"
        context += f"   Date: {item['metadata']['date']}\n"
        context += f"   Content: {item['content']}\n\n"
    
    # Add conversation history for coherence
    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history[-3:]:  # Last 3 exchanges
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current query with RAG context
    messages.append({
        "role": "user",
        "content": f"Question: {query}\n\n{context}\n\n" \
                  "Please answer based on the retrieved content above."
    })
    
    # Generate response (RAG synthesis)
    response = await openai_client.chat.completions.create(
        model="gpt-4o",  # LLM for generation
        messages=messages,
        temperature=0.7,  # Slightly creative but grounded
        max_tokens=1000
    )
    
    return response.choices[0].message.content  # Final RAG-generated answer
```     messages=messages,
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content
```

### API Endpoint

**Location**: `backend/api/views.py`

**Endpoint**: `POST /api/v1/chat/`

**Request**:
```json
{
  "query": "What are the main pain points for Nike?",
  "campaign_id": "uuid-optional",
  "conversation_history": [
    {"role": "user", "content": "Tell me about Nike campaigns"},
    {"role": "assistant", "content": "Here's what I found..."}
  ]
}
```

**Response**:
```json
{
  "response": "Based on the collected data, Nike's main pain points are:\n1. Sizing inconsistency...",
  "context_used": 8,
  "sources": [
    {
      "type": "pain_points",
      "content_preview": "Pain Point: sizing issues\nMentions: 45\n...",
      "similarity_score": 0.876,
      "source": "r/Nike",
      "date": "2025-01-15T10:30:00Z"
    }
  ],
  "tokens_used": 1250,
  "cost": 0.0085,
  "workflow_id": "wf_abc123",
  "compliance_tracked": true
}
```

**Flow**:
```
POST /api/v1/chat/
        │
        ▼
chat_query(request)
        │
        ├──▶ Validate query (required)
        ├──▶ Get Campaign (if campaign_id provided)
        ├──▶ Convert conversation_history to LangChain messages
        │
        ▼
workflow_orchestrator.execute_chat_workflow(
    user_query=query,
    conversation_history=messages,
    campaign_id=campaign_id
)
        │
        ▼
Orchestrator routes to chatbot_node
        │
        ▼
chatbot_node executes RAG workflow
        │
        ▼
Extract response from final_state.rag_context
        │
        ▼
Return Response:
    - response (text)
    - sources (list with similarity scores)
    - context_used (count)
    - tokens_used, cost
    - workflow_id
    - compliance_tracked
```

### Monitoring & Guardrails

**Guardrails Integration**:
```python
from agents.monitoring_integration import guardrails

# Query validation
validation = guardrails.validate_query(query=user_query, user_id=campaign_id)
if not validation["valid"]:
    return error_response(validation["error"])

# Output sanitization
response_text = guardrails.sanitize_output(response_text)
```

**LangSmith Tracing**:
```python
from agents.monitoring_integration import langsmith_tracer

if langsmith_tracer.enabled:
    rag_result = await langsmith_tracer.trace_query(
        query=user_query,
        rag_tool=rag_tool,  # Pure RAG implementation
        brand_id=brand_id,
        campaign_id=campaign_id,
        conversation_history=formatted_history
    )
```

**Metrics Tracked**:
- Query intent types (conversational, semantic, keyword, combined)
- Search modes executed (vector_search or combined_search)
- Context sources found from embeddings
### Vector Search Tools (Pure RAG)

**Location**: `backend/agents/vector_tools.py`

**Database**: PostgreSQL with **pgvector** extension for vector similarity search

#### Vector Search Tool
```python
class VectorSearchTool:
    """
    Pure semantic similarity search using pgvector (RAG retrieval).
    
    Process:
    1. Query text → OpenAI embedding (text-embedding-3-small)
    2. pgvector cosine similarity search (<-> operator)
    3. Return top-k results from all content types
    """
    
    async def search_all(
        query: str,
        brand_id: str,
        campaign_id: str,
        min_similarity: float = 0.5,  # Cosine similarity threshold
        limit_per_type: int = 10
    ) -> Dict[str, Any]:
        """
        Search all embedded content types using vector similarity:
        - content (generic ContentItem with embeddings)
        - insights (Insight model with embeddings)
        - pain_points (PainPoint model with embeddings)
        - threads (Thread model with embeddings)
        
        Returns results grouped by type with cosine similarity scores.
        
        SQL Example:
        SELECT *, embedding <-> query_embedding AS distance
        FROM threads
        WHERE campaign_id = ? AND embedding IS NOT NULL
        ORDER BY embedding <-> query_embedding
        LIMIT 10
        """
```

#### Combined Search Tool (Pure RAG with Dual Matching)
```python
class CombinedSearchTool:
    """
    Pure RAG using both semantic similarity AND keyword matching in vector space.
    
    Combines two scoring approaches:
    1. Semantic similarity (vector cosine distance)
    2. Keyword matching (text search in embedded content)
    
    Both operate on vector-embedded content - still pure RAG, no external APIs.
    """
    
    async def search(
        query: str,
        brand_id: str,
        campaign_id: str,
        content_type: str = "all",
        min_similarity: float = 0.5,  # Vector similarity threshold
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Combined search approach (Pure RAG with dual matching):
        1. Vector similarity search (semantic embeddings via pgvector)
        2. Keyword matching filter (exact phrase matching in content)
        3. Combined scoring: similarity * keyword_boost
        4. Unified ranking
        
        Still pure RAG - no external APIs, all vector-based.
        
        Returns unified results sorted by relevance (similarity + keyword match).
        """
```

### Conversation History Management

```python
# Track conversation in state
conversation_history = state.get("conversation_history", [])

# Format for LLM context (last 3 exchanges)
formatted_history = []
for msg in conversation_history[-6:]:  # Last 3 user + 3 assistant
    formatted_history.append({
        "role": "assistant" if isinstance(msg, AIMessage) else "user",
        "content": msg.content
    })

# Add new exchange to history
conversation_history.extend([
    HumanMessage(content=user_query),
    AIMessage(content=response_text)
])
state["conversation_history"] = conversation_history
```

### Error Handling

```python
try:
    # Execute Pure RAG workflow
    rag_result = await rag_tool.run(...)
    
    if rag_result.get("success"):
        response_text = rag_result["answer"]
        sources = rag_result["sources"]
    else:
        # Fallback on RAG failure
        error = rag_result["metadata"]["error"]
        response_text = "I encountered an issue processing your query."
        sources = []
        logger.error(f"RAG failed: {error}")
        
except Exception as e:
    # Catastrophic failure
    error_response = "I apologize, but I encountered an unexpected error."
    conversation_history.extend([
        HumanMessage(content=user_query),
        AIMessage(content=error_response)
    ])
    state["error_state"].append(f"Chatbot node failed: {e}")
    state["task_status"] = TaskStatus.FAILED
```

### Frontend Integration

**Location**: `frontend/src/components/ChatInterface.tsx`

**Features**:
- Real-time chat interface with message history
- Loading states during RAG processing
- Source citations display
- Conversation context awareness
- Error handling with user-friendly messages

**Usage Flow**:
```
User types query in ChatInterface
        ↓
Frontend sends POST /api/v1/chat/
        ↓
Backend executes chatbot_node
        ↓
Response with answer + sources
        ↓
Display in chat with citations
```

### Performance Optimizations

1. **Query Rewriting**: Contextualizes queries for better search results
2. **Intent Classification**: Routes to appropriate search strategy
3. **Similarity Threshold**: min_similarity=0.5 for better recall
4. **Result Limiting**: Top 10 results per search for speed
5. **Context Truncation**: Last 3 conversation exchanges for context
6. **Caching**: LLM suggestions cached for community discovery
7. **Parallel Execution**: Multiple tools run simultaneously when possible

### Future Enhancements

1. **Multi-modal RAG**: Support for image/video content analysis
2. **Streaming Responses**: Real-time token streaming to frontend
3. **Feedback Loop**: User ratings to improve response quality
4. **Advanced Routing**: More granular intent classification
5. **Cross-campaign Search**: Search across multiple campaigns
6. **Temporal Awareness**: Time-based context filtering
7. **Citation Links**: Direct links to source threads/insights

---

**Last Updated**: January 15, 2025
**Version**: 2.0
**Status**: Production Ready ✅

---

## Summary of Major Changes (v2.0)

### New Agent: CHATBOT AGENT (Section 6)

**Added**: Complete Pure RAG conversational AI system

**Key Features**:
- **Intent Classification**: GPT-4o-mini routing (conversational/semantic/keyword/combined)
- **Query Rewriting**: Context-aware query enhancement using conversation history
- **Pure RAG Search**: Vector embeddings with optional keyword matching (both in vector space)
- **Response Generation**: GPT-4o powered natural language synthesis from retrieved context
- **Guardrails**: Input validation and output sanitization for safety
- **LangSmith Tracing**: Full monitoring and performance tracking
- **Source Attribution**: Top sources with similarity scores from vector search

**Implementation**:
- **Location**: `backend/agents/nodes.py` - `chatbot_node()`
- **RAG Tool**: `backend/agents/rag_tool.py` - `RAGTool` class (Pure RAG)
- **API Endpoint**: `POST /api/v1/chat/`
- **Frontend**: `frontend/src/components/ChatInterface.tsx`

**Workflow**: User Query → Intent Classification → Vector Search → Context Assembly → GPT-4 Response

### SCOUT AGENT Updates (Section 2)

**Phase 5+ Major Updates**:

1. **Tavily Search API Integration** (PRIMARY DATA SOURCE):
   - **Changed from web scraping to Tavily Search API** (`from tavily import TavilyClient`)
   - LLM-driven search strategy: GPT-4 generates queries, Tavily executes searches
   - Monthly iteration: Search each month separately for temporal accuracy
   - Functions: `search_month_with_tavily_and_llm()`, `extract_threads_with_llm()`
   - API Key: `TAVILY_API_KEY` environment variable

2. **Collection Period Distinction** (Campaign-Specific):
   - **Brand Analytics (automatic monitoring)**: **6 MONTHS** historical data
     - Config: `collection_months: 6`, `search_depth: 'comprehensive'`
     - Purpose: Long-term trend analysis, dashboard intelligence
   - **Custom Campaigns (strategic focus)**: **3 MONTHS** recent data
     - Config: `collection_months: 3`, `search_depth: 'focused'`
     - Purpose: Strategic snapshot aligned with campaign objectives
   - **Changed from**: Previous 4-week collection window

3. **LLM-Driven Keyword Deduplication**:
   - Function: `_normalize_and_deduplicate_keywords()` using LLM
   - Semantic grouping: "sizing issues", "size problems", "fit concerns" → "sizing and fit issues"
   - Reduces redundant Tavily searches, improves query quality

4. **Source Discovery & Storage**:
   - As Scout searches, discovers new Reddit communities and forums
   - Stores discovered sources in `Source` model for future analysis
   - Enables learning and improving community targeting over time

5. **Resilient Data Saving** (EXISTING):
   - `resilient_bulk_save()` function for granular error handling
   - Individual item saves with continue-on-error
   - Detailed save statistics (total/succeeded/failed per type)

6. **Optimized Insight Generation** (EXISTING - 90% token reduction):
   - **Brand Analytics**: Pre-aggregate data (no LLM), single LLM call with compact summary
   - **Custom Campaigns**: Strategic report aligned with campaign objectives
   - Distinction between objective-focused vs pain-point-focused insights

**Three Celery Tasks** (See Section: Scheduled Triggers):
- `scout_reddit_task` - General periodic task, 6 months, hourly
- `scout_brand_analytics_task` - Brand monitoring, 6 months, comprehensive depth
- `scout_custom_campaign_task` - Custom campaigns, 3 months, focused depth

**New Functions**:
- `search_month_with_tavily_and_llm()` - Monthly Tavily search execution
- `extract_threads_with_llm()` - Thread extraction from Tavily results
- `_normalize_and_deduplicate_keywords()` - LLM-based keyword deduplication
- `resilient_bulk_save()` - Error-tolerant saving (EXISTING)
- `_generate_and_store_campaign_insights()` - Optimized insights (EXISTING)

### CLEANER AGENT Updates (Section 3)

**Enhanced Capabilities**:

1. **Advanced PII Detection**:
   - 5 PII types: emails, phones, SSNs, credit cards, addresses
   - Regex-based pattern matching
   - Automatic masking: `user@example.com` → `[EMAIL_REMOVED]`

2. **Multi-layer Spam Detection**:
   - 4 spam indicator categories (promotional, crypto, engagement bait)
   - Score-based filtering (threshold: 2+ indicators)
   - Compliance logging for all filtered content

3. **Toxicity Filtering**:
   - 3 toxic pattern categories (hate speech, threats, discriminatory)
   - Toxicity score (0-1) with threshold filtering (> 0.8)
   - Safety-first approach with audit trails

4. **Enhanced Sentiment Analysis**:
   - Positive/negative word detection
   - Context-aware scoring (-1 to +1)
   - Improved accuracy over basic approaches

5. **Entity & Keyword Extraction**:
   - Domain-specific keywords (product terms, quality attributes)
   - Brand entity recognition
   - Top 10 keywords per content item

6. **Duplicate Detection**:
   - Similarity-based deduplication
   - Length + content prefix comparison
   - Prevents redundant processing

7. **Quality Scoring**:
   - Length, sentence count, readability factors
   - Quality score (0-1) for content ranking

**Compliance Integration**:
- All filtering operations logged via `global_monitor.compliance_tracker`
- Audit logs for PII, spam, toxicity with confidence scores
- GDPR/CCPA compliant data handling

### ANALYST AGENT Updates (Section 4)

**Major Architecture & Feature Enhancements**:

1. **Unified Analysis Module**:
   - **Single module** for content + influencer analysis (not separate modules)
   - Consolidated in `backend/agents/analyst.py`
   - LLM: **gpt-4**, temperature=0.3 (slightly creative), max_tokens=3000

2. **4-Component Influencer Scoring**:
   - **Reach Score** (30% weight): Post volume + Engagement + Community diversity
     - Formula: `(post_count × 0.4) + (total_engagement × 0.4) + (communities × 0.2)`
   - **Authority Score** (30% weight): Consistency + Quality + Engagement ratio
     - Formula: `(consistency × 0.4) + (quality × 0.3) + (eng_ratio × 0.3)`
   - **Advocacy Score** (20% weight): Brand mention rate + Sentiment
     - Formula: `(mention_rate × 0.6) + (sentiment × 0.4)`
   - **Relevance Score** (20% weight): Mention frequency + Volume + Community relevance
     - Formula: `(frequency × 0.4) + (volume × 0.3) + (comm_relevance × 0.3)`
   - **Overall Score**: Weighted average of 4 components

3. **Pain Point to Influencer Linking**:
   - Function: `link_pain_points_to_influencers()`
   - Cross-references threads to calculate total reach per pain point
   - Sentiment breakdown (positive/negative/neutral)
   - Urgency scoring (0-10 based on growth rate + sentiment)
   - Generates actionable recommendations

4. **Comprehensive Analysis Summary**:
   - Function: `generate_comprehensive_analysis_summary()`
   - Stores in `Campaign.metadata['analysis_summary']`
   - Components:
     - Overview metrics (threads, communities, pain points, influencers)
     - Influencer breakdown (top 5 by advocacy score)
     - Urgent pain points (sorted by urgency + reach)
     - Community insights (echo scores + key influencers)
     - Key actionable insights (LLM-generated)

5. **Dashboard AI Insights** (Brand Analytics Only):
   - Function: `generate_brand_analytics_ai_insights()`
   - Uses **OpenAI o1-mini** (reasoning model) with fallback to **gpt-4**
   - Analyzes ALL dashboard data:
     - KPIs (active campaigns, high-echo communities, new pain points, positivity ratio)
     - Community Watchlist (top communities by echo score)
     - Pain Point Trends (6-month time series data)
     - Influencer Pulse (top influencers by advocacy)
     - Community × Pain Point Matrix (bubble chart data)
     - Total Mention Volume Trend (6-month aggregated data)
   - Generates **6 strategic insights** covering:
     1. Brand health assessment (echo scores + positivity + trends)
     2. Community engagement opportunities (matrix + bubble chart analysis)
     3. Pain point analysis (time series trends + growth patterns)
     4. Influencer strategy (partnership opportunities + gaps)
     5. Trend analysis (6-month patterns + seasonality detection)
     6. Strategic recommendations (immediate actions with specific data)
   - Output: List of 6 insights (1-2 sentences each, executive-level language)
   - Displayed in Dashboard "AI-Powered Key Insights" section

6. **Strategic Campaign Report** (Custom Campaigns):
   - Function: `generate_strategic_campaign_report()`
   - Executive summary aligned with campaign objectives
   - Strategic findings with priority rankings (high/medium/low)
   - Key metrics and supporting data
   - Recommended next steps
   - PDF generation: `generate_strategic_report_pdf()`

**New Functions**:
- `analyze_influencers_for_threads()` - Unified influencer analysis
- `aggregate_user_metrics_from_threads()` - User activity aggregation
- `calculate_influence_scores()` - 4-component scoring
- `link_pain_points_to_influencers()` - Pain point impact analysis
- `generate_comprehensive_analysis_summary()` - Campaign metadata summary
- `generate_brand_analytics_ai_insights()` - Dashboard AI insights with o1-mini
- `generate_strategic_campaign_report()` - Custom campaign reports
- `generate_strategic_report_pdf()` - PDF export

### ORCHESTRATOR Updates (Section 1)

**Routing Enhancements**:

1. **Chat Query Routing**:
   - New route: `task_type == "chat_query"` → `chatbot_node`
   - Direct path bypasses Scout/Cleaner/Analyst
   - Optimized for fast query responses

2. **Conditional Edge Configuration**:
   ```python
   workflow.add_conditional_edges(
       "start",
       route_workflow,
       {
           "scout_content": "scout_content",
           "chat_query": "chatbot_node",  # NEW
           "monitoring": "monitoring_agent"
       }
   )
   ```

3. **Chat Workflow Path**:
   - `start` → `chatbot_node` → `monitoring_agent` → `finalize_workflow` → `END`
   - No data collection or cleaning needed for RAG queries

### Architecture Changes

**Updated System Architecture Diagram**:
- Added **CHATBOT AGENT** as 4th primary agent
- Added **Chat Interface** to user interactions
- Enhanced database with **pgvector** for embeddings
- **Agent Routing Logic** diagram showing 4 task types

**New Database Components**:
- **Embeddings**: Vector representations for RAG search
- **Conversation History**: Chat context storage
- **RAG Context**: Query results and sources

**Monitoring Enhancements**:
- **RAG Interaction Tracking**: Query intents, tools executed, context sources
- **Response Quality Metrics**: Relevance, coherence, citation accuracy
- **Guardrail Monitoring**: Validation failures, output sanitization

### User-Initiated Triggers (Section 4)

**New Trigger: Chat Query**:
- **Endpoint**: `POST /api/v1/chat/`
- **Request**: query, optional campaign_id, conversation_history
- **Response**: answer, sources (with similarity scores), tokens, cost
- **Flow**: ChatInterface → API → Orchestrator → Chatbot Node → RAG Tool → Response

### Key Metrics Improvements

**Scout Agent**:
- **Data Source**: Tavily Search API (replaced web scraping) with LLM-driven queries
- **Collection Period**: 6 months (Brand Analytics), 3 months (Custom Campaigns)
- **Monthly Iteration**: Search per month for temporal accuracy and trend detection
- **Keyword Optimization**: LLM-based semantic deduplication (reduces redundant searches)
- **Source Discovery**: Automatic storage of discovered Reddit communities and forums
- **Token Reduction**: 90% for Brand Analytics (pre-aggregation + single LLM call)
- **Save Reliability**: Individual item error handling with detailed statistics

**Chatbot Agent (Pure RAG)**:
- **Response Time**: < 2s for most queries (pgvector search + GPT-4 synthesis)
- **Vector Similarity**: min_similarity=0.5 (cosine distance threshold)
- **Token Efficiency**: Intent classification with GPT-4o-mini (fast, cheap)
- **Conversation Context**: Last 3 exchanges for coherence
- **RAG Workflow**: Query embedding → pgvector search → top-k results → GPT-4 synthesis

**Analyst Agent**:
- **Influencer Scoring**: 4-component model (Reach 30%, Authority 30%, Advocacy 20%, Relevance 20%)
- **LLM Model**: gpt-4 (temperature=0.3, max_tokens=3000) for analysis
- **Dashboard Insights**: o3-mini (reasoning model) with gpt-4 fallback
- **Insight Generation**: 6 strategic insights from all dashboard data (KPIs + charts + time series)
- **Pain Point Linking**: Cross-referenced with influencers for reach + sentiment + urgency
- **PDF Export**: Strategic reports with priority rankings and recommendations

**Cleaner Agent**:
- **PII Detection**: 5 types with 100% masking coverage
- **Spam Filter Rate**: ~5-10% filtered (based on indicators)
- **Toxicity Threshold**: 0.8 (safety-first approach)
- **Processing Speed**: ~100ms per item (rule-based + selective LLM)

---

## Version History

### v2.0 (November 05, 2025)
- ✅ Added CHATBOT AGENT with **pure RAG system** (pgvector + GPT-4)
- ✅ Scout Agent: **Tavily Search API** + **6-month/3-month periods** + LLM-driven queries + monthly iteration + keyword deduplication + source discovery
- ✅ Analyst Agent: **Unified module** + **4-component influencer scoring** + **o3-mini Dashboard insights** + pain point linking + strategic reports + PDF export
- ✅ Cleaner Agent: 5 PII types, toxicity filtering, enhanced sentiment
- ✅ Orchestrator: Chat query routing with conditional edges
- ✅ Celery Tasks: **3 scout tasks** (general, brand_analytics, custom_campaign) with distinct configs
- ✅ Monitoring: RAG interaction tracking, guardrails integration
- ✅ Documentation: Complete agent workflows, API endpoints, RAG architecture, Tavily integration

### v1.0 (October 22, 2024)
- Initial documentation
- Scout, Cleaner, Analyst, Monitoring agents
- Basic workflow orchestration
- Dashboard integration

---

**Last Updated**: November 6, 2025
**Version**: 2.0
**Status**: Production Ready ✅
