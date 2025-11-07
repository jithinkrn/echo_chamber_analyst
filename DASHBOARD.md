# Dashboard Analytics Documentation

**Version**: 2.0  
**Last Updated**: November 6, 2025  
**Purpose**: Complete documentation of dashboard calculations, formulas, and logic

---

## Table of Contents

1. [Brand Analytics Dashboard](#1-brand-analytics-dashboard)
   - 1.1 [KPI Cards](#11-kpi-cards)
   - 1.2 [Top-Growing Pains Bar Chart](#12-top-growing-pains-bar-chart)
   - 1.3 [Communities × Pain Points Scatter Chart](#13-communities--pain-points-scatter-chart)
   - 1.4 [Pain Point Trends (Time Series)](#14-pain-point-trends-time-series)
   - 1.5 [Community Watchlist](#15-community-watchlist)
   - 1.6 [Influencer Pulse](#16-influencer-pulse)
   - 1.7 [AI-Powered Key Insights](#17-ai-powered-key-insights)

2. [Campaign Analytics Dashboard](#2-campaign-analytics-dashboard)
   - 2.1 [Campaign Overview Cards](#21-campaign-overview-cards)
   - 2.2 [Key Campaign Insights](#22-key-campaign-insights)
   - 2.3 [Strategic Report Generation](#23-strategic-report-generation)
   - 2.4 [Report Export (PDF)](#24-report-export-pdf)

---

## 1. Brand Analytics Dashboard

**Scope**: Automatic Brand Analytics campaigns only (`campaign_type='automatic'`)  
**Data Source**: 6 months of historical data collected via Tavily Search API  
**Location**: `backend/api/views.py` - `get_brand_dashboard_kpis()`, `get_brand_top_pain_points()`, etc.

---

### 1.1 KPI Cards

**Function**: `get_brand_dashboard_kpis(brand_id, date_from, date_to)`  
**Display**: 4 KPI cards at the top of the dashboard

#### 1.1.1 Active Campaigns

**Calculation**:
```python
active_campaigns_count = Campaign.objects.filter(
    brand_id=brand_id,
    campaign_type='automatic',
    status__in=['active', 'running']
).count()
```

**Logic**:
- Counts campaigns with status = 'active' OR 'running'
- Only includes automatic (Brand Analytics) campaigns
- Excludes completed, paused, or archived campaigns

**Display**: Integer count (e.g., "2")

---

#### 1.1.2 High-Echo Communities

**Calculation**:
```python
high_echo_communities_count = Community.objects.filter(
    brand_id=brand_id,
    campaign=automatic_campaign,
    echo_score__gte=7.0,
    is_active=True
).count()
```

**Logic**:
- Communities with Echo Score ≥ 7.0 out of 10.0
- Must be marked as active (`is_active=True`)
- Only from Brand Analytics automatic campaign

**Echo Score Formula** (see Section 1.5 for details):
```
Echo Score = Thread Volume (40%) + Pain Point Intensity (30%) + Engagement Depth (30%)
```

**Trend Calculation** (7-day change):
```python
seven_days_ago = datetime.now() - timedelta(days=7)
previous_high_echo = brand_communities.filter(
    last_analyzed__lt=seven_days_ago
).count()

high_echo_change = ((high_echo_communities_count - previous_high_echo) / previous_high_echo) * 100
```

**Display**: 
- Count: Integer (e.g., "12")
- Trend: Percentage with +/- sign (e.g., "+15.2%")

---

#### 1.1.3 New Pain Points

**Calculation**:
```python
# Get last 6 COMPLETED months (excluding current incomplete month)
month_years = []
current_date = datetime.now()
for i in range(1, 7):  # Months 1-6 (skip month 0 = current)
    month_date = current_date - relativedelta(months=i)
    month_years.append(month_date.strftime('%Y-%m'))

# Latest completed month
latest_month = month_years[0]  # e.g., "2025-10"
previous_months = month_years[1:]  # Previous 5 months

# Get keywords from latest month
latest_month_keywords = set(
    PainPoint.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign,
        month_year=latest_month
    ).values_list('keyword', flat=True).distinct()
)

# Get keywords from previous 5 months
previous_months_keywords = set(
    PainPoint.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign,
        month_year__in=previous_months
    ).values_list('keyword', flat=True).distinct()
)

# NEW pain points = keywords in latest month NOT in previous months
new_pain_points_count = len(latest_month_keywords - previous_months_keywords)
```

**Logic**:
- **Definition**: Pain point keywords appearing in the latest completed month (e.g., October 2025) that did NOT appear in any of the previous 5 completed months
- Uses set difference to find unique keywords
- **Example**: If October has keywords `["sizing", "color", "durability"]` and previous months only had `["sizing", "color"]`, then `new_pain_points_count = 1` (durability is new)
- Excludes current incomplete month to avoid false positives

**Display**: Integer count (e.g., "8 new pain points")

---

#### 1.1.4 Positivity Ratio

**Calculation**:
```python
# Get pain points from latest completed month with real sentiment data
latest_month_pain_points = PainPoint.objects.filter(
    campaign=automatic_campaign,
    month_year=latest_month
).exclude(sentiment_score=0.0)  # Exclude default zero values

# If no data, try previous months
if not latest_month_pain_points.exists():
    for month in month_years[1:]:  # Try months 2-6
        latest_month_pain_points = PainPoint.objects.filter(
            campaign=automatic_campaign,
            month_year=month
        ).exclude(sentiment_score=0.0)
        if latest_month_pain_points.exists():
            break

# Calculate average sentiment
if latest_month_pain_points.exists():
    avg_sentiment = latest_month_pain_points.aggregate(
        avg_sentiment=Avg('sentiment_score')
    )['avg_sentiment'] or 0.0
    
    # Convert sentiment (-1 to +1) to percentage (0 to 100)
    positivity_ratio = max(0, min(100, (avg_sentiment + 1) * 50))
else:
    positivity_ratio = 0.0
```

**Formula**:
```
Positivity Ratio = ((avg_sentiment + 1) / 2) × 100

Where:
- avg_sentiment ranges from -1 (very negative) to +1 (very positive)
- positivity_ratio ranges from 0% (all negative) to 100% (all positive)
- 50% = neutral sentiment (avg_sentiment = 0)
```

**Examples**:
- `avg_sentiment = -1.0` → `positivity_ratio = 0%` (all negative)
- `avg_sentiment = -0.5` → `positivity_ratio = 25%` (mostly negative)
- `avg_sentiment = 0.0` → `positivity_ratio = 50%` (neutral)
- `avg_sentiment = +0.5` → `positivity_ratio = 75%` (mostly positive)
- `avg_sentiment = +1.0` → `positivity_ratio = 100%` (all positive)

**Trend Calculation** (7-day change in percentage points):
```python
fourteen_days_ago = datetime.now() - timedelta(days=14)
previous_threads = Thread.objects.filter(
    brand_id=brand_id,
    campaign=automatic_campaign,
    analyzed_at__gte=fourteen_days_ago,
    analyzed_at__lt=seven_days_ago
)

prev_avg_sentiment = previous_threads.aggregate(
    avg_sentiment=Avg('sentiment_score')
)['avg_sentiment'] or 0

prev_positivity_ratio = max(0, min(100, (prev_avg_sentiment + 1) * 50))

# Percentage point change (not percentage change)
positivity_change_pp = positivity_ratio - prev_positivity_ratio
```

**Display**: 
- Ratio: Percentage (e.g., "68.5%")
- Trend: Percentage points with +/- (e.g., "+2.3pp")

---

### 1.2 Top-Growing Pains Bar Chart

**Function**: `get_brand_top_pain_points(brand_id, date_from, date_to, limit=10)`  
**Display**: Horizontal bar chart showing top 10 pain points by volume

#### Calculation Logic

```python
# 1. Get all pain points from automatic campaign
pain_points = PainPoint.objects.filter(
    brand_id=brand_id,
    campaign=automatic_campaign
).values('keyword', 'month_year', 'mention_count')

# 2. Aggregate mentions by keyword and month (handle duplicates)
pain_point_data = defaultdict(lambda: {'months': {}})

for pp in pain_points:
    keyword = pp['keyword']
    month_year = pp['month_year']
    mention_count = pp['mention_count']
    
    if month_year not in pain_point_data[keyword]['months']:
        pain_point_data[keyword]['months'][month_year] = 0
    pain_point_data[keyword]['months'][month_year] += mention_count

# 3. Calculate average mentions across 6 months
last_6_months = []  # ['2025-05', '2025-06', ..., '2025-10']
for offset in range(6, 0, -1):
    target_date = now - relativedelta(months=offset)
    month_year = target_date.strftime('%Y-%m')
    last_6_months.append(month_year)

pain_points_with_growth = []
for keyword, data in pain_point_data.items():
    # Get mentions per month
    all_months_mentions = [data['months'].get(month, 0) for month in last_6_months]
    
    # Calculate averages
    avg_mentions = sum(all_months_mentions) / len(last_6_months)
    total_mentions = sum(data['months'].values())
    
    # Only include meaningful pain points (avg >= 0.5 = at least 3 mentions total)
    if avg_mentions >= 0.5:
        pain_points_with_growth.append({
            'keyword': keyword,
            'mention_count': total_mentions,
            'avg_mentions': round(avg_mentions, 1),
            'recent_avg_mentions': round(avg_mentions, 1)
        })

# 4. Sort by average mention volume (highest first)
pain_points_with_growth.sort(key=lambda x: x['avg_mentions'], reverse=True)

# 5. Return top 10
return pain_points_with_growth[:10]
```

#### Key Logic

**Sorting Criteria**: Average mention volume across 6 months (NOT growth rate)
- Shows the most talked-about issues
- Higher average = more critical pain point
- Captures both consistent and trending issues

**Why not growth rate?**
- Growth rate can be misleading (e.g., 1 mention → 2 mentions = 100% growth but low impact)
- Volume is more actionable: "sizing issues" with 120 mentions is more critical than "button color" with 5 mentions even if the latter grew faster

**Display**:
- X-axis: Average mentions per month
- Y-axis: Pain point keywords (top 10)
- Bar color: Can be mapped to sentiment (red = negative, yellow = neutral, green = positive)
- Tooltip: Total mentions, average mentions, sentiment score

---

### 1.3 Communities × Pain Points Scatter Chart

**Function**: `get_brand_heatmap_data(brand_id, date_from, date_to)` → `community_pain_point_matrix`  
**Display**: Bubble chart with communities on Y-axis, pain points on X-axis

#### Calculation Logic

```python
# 1. Get top 5 communities by echo score
top_communities = Community.objects.filter(
    brand_id=brand_id,
    campaign=automatic_campaign
).order_by('-echo_score')[:5]

community_matrix = []

# 2. For each community, get top 5 pain points
for community in top_communities:
    # Aggregate pain points across all months for this community
    community_pain_points_raw = PainPoint.objects.filter(
        community=community
    ).values('keyword').annotate(
        total_mentions=Sum('mention_count'),
        avg_heat=Avg('heat_level'),
        avg_sentiment=Avg('sentiment_score')
    ).order_by('-total_mentions')[:5]
    
    community_pain_points = []
    
    # 3. Calculate growth for each pain point
    for pp in community_pain_points_raw:
        # Get monthly data sorted chronologically
        monthly_data = list(PainPoint.objects.filter(
            community=community,
            keyword=pp['keyword']
        ).order_by('month_year').values_list('month_year', 'mention_count'))
        
        first_month_count = monthly_data[0][1] if len(monthly_data) > 0 else 0
        recent_month_count = monthly_data[-1][1] if len(monthly_data) > 0 else 0
        
        # Calculate growth percentage
        if first_month_count > 0 and recent_month_count != first_month_count:
            growth = ((recent_month_count - first_month_count) / first_month_count) * 100
        else:
            growth = 0.0
        
        community_pain_points.append({
            'keyword': pp['keyword'],
            'mention_count': pp['total_mentions'],
            'heat_level': int(pp['avg_heat']),
            'sentiment_score': float(pp['avg_sentiment']),
            'growth_percentage': round(growth, 1)
        })
    
    # 4. Add to matrix (even if no pain points)
    community_matrix.append({
        'community_name': community.name,
        'platform': community.platform,
        'echo_score': float(community.echo_score),
        'pain_points': community_pain_points  # Can be empty list
    })
```

#### Visualization

**Bubble Characteristics**:
- **Position**: Community (Y) × Pain Point (X)
- **Bubble Size**: `mention_count` (larger = more mentions)
- **Bubble Color**: `growth_percentage` (green = positive growth, red = declining)
- **Hover Data**: keyword, mention_count, sentiment_score, heat_level, growth_percentage

**Purpose**: 
- Identify which communities discuss which pain points
- Spot high-impact combinations (high echo score + high mention count)
- Prioritize engagement strategy

**Example**:
```
Community: r/Nike (Echo Score: 8.5)
Pain Points:
  - sizing issues: 45 mentions, +25% growth, sentiment: -0.45
  - delivery delays: 32 mentions, +10% growth, sentiment: -0.60
  - quality concerns: 28 mentions, -5% growth, sentiment: -0.35
```

---

### 1.4 Pain Point Trends (Time Series)

**Function**: `get_brand_heatmap_data(brand_id, date_from, date_to)` → `time_series_pain_points` + `total_mentions_series`  
**Display**: Multi-line chart showing pain point trends over 6 months

#### Calculation Logic

```python
# 1. Get all unique pain point keywords
all_keywords_raw = PainPoint.objects.filter(
    brand_id=brand_id,
    campaign=automatic_campaign
).values_list('keyword', flat=True)

all_pain_point_keywords = list(dict.fromkeys(all_keywords_raw))  # Deduplicate

# 2. Generate time buckets (6 completed months)
time_buckets = []
for offset in range(6, 0, -1):  # 6 months ago to 1 month ago
    target_date = now - relativedelta(months=offset)
    month_year = target_date.strftime('%Y-%m')  # "2025-05"
    month_label = target_date.strftime('%b %Y')  # "May 2025"
    
    time_buckets.append({
        'month_year': month_year,
        'month_label': month_label
    })

# 3. Calculate total mentions across ALL pain points per month
total_mentions_series = []
for bucket in time_buckets:
    total_count = PainPoint.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign,
        month_year=bucket['month_year']
    ).aggregate(total=Sum('mention_count'))['total'] or 0
    
    total_mentions_series.append({
        'label': bucket['month_label'],
        'date': bucket['month_label'],
        'total_mentions': total_count
    })

# 4. For each pain point keyword, get monthly mentions
time_series_matrix = []

for keyword in all_pain_point_keywords:
    pain_point_time_data = {
        'keyword': keyword,
        'time_series': []
    }
    
    # Get mentions per month
    for bucket in time_buckets:
        month_pain_points = PainPoint.objects.filter(
            keyword=keyword,
            month_year=bucket['month_year']
        ).aggregate(
            total_mentions=Sum('mention_count'),
            avg_sentiment=Avg('sentiment_score'),
            avg_heat=Avg('heat_level')
        )
        
        pain_point_time_data['time_series'].append({
            'label': bucket['month_label'],
            'date': bucket['month_label'],
            'mention_count': month_pain_points['total_mentions'] or 0,
            'sentiment_score': float(month_pain_points['avg_sentiment'] or 0.0),
            'heat_level': int(month_pain_points['avg_heat'] or 1)
        })
    
    # 5. Calculate month-over-month growth rate
    time_series = pain_point_time_data['time_series']
    if len(time_series) >= 2:
        previous_month = time_series[-2]['mention_count']
        current_month = time_series[-1]['mention_count']
        
        if previous_month > 0:
            growth_rate = ((current_month - previous_month) / previous_month) * 100
        elif current_month > 0:
            growth_rate = 100.0
        else:
            growth_rate = 0.0
    else:
        growth_rate = 0.0
    
    pain_point_time_data['growth_rate'] = round(growth_rate, 1)
    pain_point_time_data['total_mentions'] = sum(tp['mention_count'] for tp in time_series)
    
    time_series_matrix.append(pain_point_time_data)

# 6. Sort by total mentions (most mentioned first)
time_series_matrix = sorted(time_series_matrix, key=lambda x: x['total_mentions'], reverse=True)
```

#### Display Components

**1. Total Mention Volume Line** (aggregate trend):
- X-axis: Months (May 2025, Jun 2025, ..., Oct 2025)
- Y-axis: Total mentions across all pain points
- Line color: Blue (primary trend line)
- Purpose: Shows overall discussion volume

**2. Individual Pain Point Lines** (top 5-10):
- X-axis: Months
- Y-axis: Mentions per pain point
- Line colors: Distinct colors per pain point
- Tooltip: keyword, mention_count, sentiment_score, growth_rate
- Purpose: Identify accelerating vs. declining pain points

**Key Insights**:
- **Accelerating**: Growth rate > 20% (critical, needs attention)
- **Stable**: Growth rate -10% to +10% (ongoing issue)
- **Declining**: Growth rate < -20% (resolved or less relevant)
- **Seasonal**: Patterns repeating monthly (e.g., holiday shipping issues)

---

### 1.5 Community Watchlist

**Function**: `get_brand_community_watchlist(brand_id)`  
**Display**: Table showing top 5 communities by echo score

#### Calculation Logic

```python
# 1. Get top 5 communities by echo score
brand_communities = Community.objects.filter(
    brand_id=brand_id,
    campaign=automatic_campaign,
    is_active=True
).distinct().order_by('-echo_score')[:5]

watchlist_data = []

# 2. For each community, identify key influencer
for rank, community in enumerate(brand_communities, 1):
    threads = Thread.objects.filter(community=community)
    
    # Find most active author (by post count and engagement)
    author_stats = threads.values('author').annotate(
        post_count=Count('id'),
        total_upvotes=Sum('upvotes'),
        total_comments=Sum('comment_count')
    ).filter(
        ~Q(author='unknown') & ~Q(author='') & ~Q(author__isnull=True)
    ).order_by('-post_count', '-total_upvotes')
    
    if author_stats.exists():
        top_author = author_stats.first()
        key_influencer = top_author['author']
        influencer_post_count = top_author['post_count']
        influencer_engagement = (top_author['total_upvotes'] or 0) + 
                                (top_author['total_comments'] or 0)
        
        # Get URL from one thread by this author
        sample_thread = threads.filter(author=key_influencer).first()
        influencer_url = sample_thread.url if sample_thread else None
    else:
        # No valid authors found
        key_influencer = 'Not identified'
        influencer_post_count = 0
        influencer_engagement = 0
        influencer_url = None
    
    watchlist_data.append({
        'id': community.id,
        'rank': rank,
        'name': community.name,
        'platform': community.platform,
        'member_count': community.member_count,
        'echo_score': float(community.echo_score),
        'key_influencer': key_influencer,
        'influencer_post_count': influencer_post_count,
        'influencer_engagement': influencer_engagement,
        'influencer_url': influencer_url
    })
```

#### Echo Score Formula (0-100)

**Function**: `calculate_community_echo_score(community_id, months=6)`  
**Location**: `backend/common/utils.py`

```python
# Component 1: Thread Volume Score (40% weight)
thread_count = Thread.objects.filter(community=community).count()
thread_score = min(40, thread_count * 2)
# Max score: 20+ threads = 40 points

# Component 2: Pain Point Intensity Score (30% weight)
unique_pain_points = PainPoint.objects.filter(
    community=community
).values('keyword').distinct().count()
pain_point_score = min(30, unique_pain_points * 3)
# Max score: 10+ unique pain points = 30 points

# Component 3: Engagement Depth Score (30% weight)
engagement_data = Thread.objects.filter(community=community).aggregate(
    total_upvotes=Sum('upvotes'),
    total_comments=Sum('comment_count')
)
upvotes = engagement_data['total_upvotes'] or 0
comments = engagement_data['total_comments'] or 0
total_engagement = upvotes + comments
engagement_score = min(30, total_engagement / 20)
# Max score: 600+ total engagement = 30 points

# Total Echo Score
echo_score = thread_score + pain_point_score + engagement_score
```

**Formula Breakdown**:

| Component | Weight | Calculation | Max Points | Purpose |
|-----------|--------|-------------|------------|---------|
| **Thread Volume** | 40% | `min(40, thread_count × 2)` | 40 | Measures brand mention frequency |
| **Pain Point Intensity** | 30% | `min(30, unique_pain_points × 3)` | 30 | Identifies critical issue discussions |
| **Engagement Depth** | 30% | `min(30, total_engagement ÷ 20)` | 30 | Captures community activity level |

**Score Interpretation**:
- **0-3.0**: Low echo (minimal brand discussion)
- **3.0-5.0**: Moderate echo (some brand presence)
- **5.0-7.0**: Good echo (active brand discussions)
- **7.0-10.0**: High echo (**high-echo communities**, critical for monitoring)

**Example Calculation**:
```
Community: r/Nike
- Threads: 25 → thread_score = min(40, 25 × 2) = 40
- Pain Points: 12 → pain_point_score = min(30, 12 × 3) = 30
- Engagement: 850 → engagement_score = min(30, 850 ÷ 20) = 30
→ Echo Score = 40 + 30 + 30 = 100 (capped at 10.0 in practice)

Actually: echo_score = round(100 / 10, 1) = 10.0
```

**Display**:
- Rank, Community Name, Platform, Member Count
- Echo Score (0-10 with 1 decimal)
- Key Influencer (username), Post Count, Engagement
- Link to influencer's profile/thread

---

### 1.6 Influencer Pulse

**Function**: `get_brand_influencer_pulse(brand_id)`  
**Display**: Table showing top 5 micro-influencers (reach < 50k)

#### Calculation Logic

```python
# Get influencers for Brand Analytics
brand_influencers = Influencer.objects.filter(
    brand_id=brand_id,
    campaign=automatic_campaign,
    reach__lt=50000,  # Micro-influencers only
    reach__gt=0
).order_by('-engagement_rate')[:5]

influencer_data = []
for influencer in brand_influencers:
    # Get topics they discuss
    topics_text = ', '.join(influencer.topics) if influencer.topics else \
                  influencer.content_topics[0] if influencer.content_topics else \
                  'general discussion'
    
    influencer_data.append({
        'handle': influencer.username,
        'platform': influencer.source_type,
        'reach': influencer.reach,
        'engagement_rate': float(influencer.engagement_rate),
        'topics_text': topics_text[:50] + '...' if len(topics_text) > 50 else topics_text
    })
```

#### Influencer Scoring (from analyst.py)

**4-Component Influence Score** (0-100):

1. **Reach Score (30% weight)**:
   ```python
   reach_score = (post_count × 0.4) + (total_engagement × 0.4) + (communities × 0.2)
   ```
   - Post count: Number of posts/threads created
   - Total engagement: Sum of upvotes + comments
   - Communities: Number of distinct communities where active

2. **Authority Score (30% weight)**:
   ```python
   authority_score = (consistency × 0.4) + (quality × 0.3) + (eng_ratio × 0.3)
   ```
   - Consistency: Posting frequency over time
   - Quality: Average upvotes per post
   - Engagement ratio: Comments per post

3. **Advocacy Score (20% weight)**:
   ```python
   advocacy_score = (mention_rate × 0.6) + (sentiment × 0.4)
   ```
   - Mention rate: Percentage of posts mentioning the brand
   - Sentiment: Average sentiment of brand mentions

4. **Relevance Score (20% weight)**:
   ```python
   relevance_score = (frequency × 0.4) + (volume × 0.3) + (comm_relevance × 0.3)
   ```
   - Frequency: How often they mention brand
   - Volume: Total number of brand mentions
   - Community relevance: Relevance to brand's target communities

**Overall Influence Score**:
```python
influence_score = (reach × 0.3) + (authority × 0.3) + (advocacy × 0.2) + (relevance × 0.2)
```

**Why Micro-Influencers (< 50k)?**
- Higher engagement rates (often 5-10% vs. 1-2% for macro-influencers)
- More authentic and trusted by niche communities
- Cost-effective for partnerships
- Better brand alignment and advocacy

**Display**:
- Handle, Platform, Reach (followers)
- Engagement Rate (percentage)
- Topics (comma-separated list of discussion topics)
- Advocacy Score (0-10)

---

### 1.7 AI-Powered Key Insights

**Function**: `generate_brand_analytics_ai_insights(brand, kpis, communities, pain_points, influencers, heatmap_data)`  
**Location**: `backend/agents/analyst.py`  
**LLM Model**: OpenAI **o1-mini** (reasoning model) with fallback to **gpt-4**

#### Input Data

The AI receives ALL dashboard data:

```python
dashboard_data = f"""BRAND ANALYTICS DASHBOARD DATA - {brand.name}

INDUSTRY: {brand.industry or 'Not specified'}
ANALYSIS PERIOD: Last 6 completed months

📊 KEY PERFORMANCE INDICATORS (KPIs):
• Active Campaigns: {kpis['active_campaigns']}
• High-Echo Communities (score ≥7.0): {kpis['high_echo_communities']}
  └─ Trend: {kpis['high_echo_change_percent']}% change
• New Pain Points: {kpis['new_pain_points_above_50']} keywords in latest month only
  └─ Change: {kpis['new_pain_points_change']} new issues
• Positivity Ratio: {kpis['positivity_ratio']}%
  └─ Trend: {kpis['positivity_change_pp']} percentage points change

🌐 COMMUNITY WATCHLIST ({len(communities)} communities):
Top Communities by Echo Score:
  1. {community.name} ({community.platform})
     • Echo Score: {community.echo_score}/100
     • Members: {community.member_count:,}
     • Key Influencer: {community.key_influencer} ({posts} posts, {engagement} engagement)

⚠️ PAIN POINT TRENDS ({len(pain_points)} total):
Top Growing Pain Points:
  • {keyword}
    └─ {mention_count} total mentions across communities
    └─ Growth Rate: +{growth_percentage}% month-over-month
    └─ Sentiment: {sentiment_score} (scale: -1 to +1)

👥 INFLUENCER PULSE ({len(influencers)} influencers):
Top Influencers:
  • @{handle} ({platform})
    └─ Reach: {reach:,} followers
    └─ Engagement Rate: {engagement_rate}%
    └─ Advocacy Score: {advocacy_score}/10

📈 COMMUNITY × PAIN POINT MATRIX (bubble chart):
  • {community_name} ({platform}) - Echo Score: {echo_score}
    └─ {keyword}: {mention_count} mentions, +{growth_percentage}% growth, sentiment {sentiment}

📊 PAIN POINT TRENDS OVER TIME (6-month time series):
  • {keyword}: {total_mentions} total mentions, {growth_rate}% MoM growth
    └─ Recent trend: Oct: 45, Sep: 38, Aug: 32

📉 TOTAL MENTION VOLUME TREND (all pain points combined):
  • Oct 2025: 1,250 total mentions
  • Sep 2025: 1,180 total mentions
  Overall 6-month trend: 📈 INCREASING (+15.3%)
"""
```

#### Prompt Instructions

```
Generate exactly 6 strategic, actionable insights covering:

1. BRAND HEALTH ASSESSMENT: Evaluate overall brand perception based on echo scores, 
   positivity ratio, community engagement patterns, and 6-month mention volume trend. 
   Reference specific trend data.

2. COMMUNITY ENGAGEMENT OPPORTUNITIES: Analyze community watchlist AND matrix to 
   identify best opportunities for brand advocacy, partnerships, or crisis management.

3. PAIN POINT ANALYSIS: Examine top growing pain points list AND time series to 
   identify critical issues. Note accelerating growth, seasonal spikes, or decline.

4. INFLUENCER STRATEGY: Evaluate influencer landscape for partnership opportunities, 
   brand advocates, or gaps. Cross-reference with community data.

5. TREND ANALYSIS: Use 6-month time series to identify patterns (increasing/decreasing, 
   accelerating/decelerating, seasonal patterns).

6. STRATEGIC RECOMMENDATIONS: Provide prioritized action items with immediate business 
   impact. Reference specific numbers from time series and matrix data.

FORMAT: Return ONLY 6 insights, numbered 1-6. Each 1-2 sentences max. 
Be specific with actual numbers. Use executive-level language.
```

#### LLM Configuration

**Primary Model**: `o1-mini`
```python
response = client.chat.completions.create(
    model="o3-mini",  # OpenAI's reasoning model
    messages=[{
        "role": "user",
        "content": prompt
    }]
)
```

**Fallback Model**: `gpt-4`
```python
# If o3-mini fails
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are an expert brand intelligence analyst..."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7,
    max_tokens=800
)
```

**Why o1-mini?**
- **Reasoning capability**: Better at connecting data points across multiple charts
- **Strategic thinking**: Identifies patterns humans might miss
- **Conciseness**: Generates executive-level insights (not verbose explanations)
- **Fallback safety**: If unavailable, gpt-4 provides reliable alternative

#### Output Format

```python
insights = [
    "Brand health is strong with 68.5% positivity ratio (+2.3pp) and 12 high-echo communities (+15.2%), indicating growing positive sentiment and community engagement over the past 6 months.",
    
    "r/Nike (Echo Score: 8.5) shows 45 mentions of 'sizing issues' with +25% growth and -0.45 sentiment; immediate product team review recommended to prevent escalation.",
    
    "Pain point 'delivery delays' accelerating at +40% MoM (Oct: 38 mentions, Sep: 27) despite overall mention volume declining by -5%; logistics partner review urgent.",
    
    "Top influencer @sneaker_reviews (25k reach, 8.5% engagement, 8.2 advocacy score) has 85% positive sentiment; prime candidate for brand ambassador program.",
    
    "6-month trend shows seasonal spike in 'quality concerns' every Q4 (+60% in Oct vs. Jul), suggesting holiday production rush issues; proactive Q4 2026 planning needed.",
    
    "Strategic action: Allocate 40% of community engagement budget to r/Nike and r/Sneakers (combined 180k members, Echo 8.5+) to address top 3 pain points before Black Friday."
]
```

**Display**:
- 6 numbered insights in card format
- Each insight 1-2 sentences
- Includes specific data points (numbers, percentages, names)
- Prioritized by urgency and business impact
- Actionable recommendations

---

## 2. Campaign Analytics Dashboard

**Scope**: Custom Campaigns only (`campaign_type='custom'`)  
**Data Source**: 3 months of focused data collected via Tavily Search API  
**Location**: `backend/api/views.py` - `get_brand_campaign_analytics()`

---

### 2.1 Campaign Overview Cards

**Function**: `get_brand_campaign_analytics(brand_id, date_from, date_to)`  
**Display**: 6 metric cards

#### Calculated Metrics

```python
# Get custom campaigns only
custom_campaigns = Campaign.objects.filter(
    brand_id=brand_id,
    campaign_type='custom'
)

# 1. Total Campaigns
total_campaigns = custom_campaigns.count()

# 2. Active Campaigns
active_campaigns = custom_campaigns.filter(status='active').count()

# 3. Completed Campaigns
completed_campaigns = custom_campaigns.filter(status='completed').count()

# 4. Paused Campaigns
paused_campaigns = custom_campaigns.filter(status='paused').count()

# 5. Total Budget
total_budget = custom_campaigns.aggregate(
    total=Sum('daily_budget')
)['total'] or 0

# 6. Total Spent
total_spent = custom_campaigns.aggregate(
    total=Sum('current_spend')
)['total'] or 0

# 7. Budget Utilization
budget_utilization = round(
    (total_spent / total_budget * 100) if total_budget > 0 else 0, 
    1
)
```

**Card Display**:

| Card | Value | Calculation |
|------|-------|-------------|
| **Total Campaigns** | Integer | Count of all custom campaigns |
| **Active** | Integer | Status = 'active' |
| **Completed** | Integer | Status = 'completed' |
| **Paused** | Integer | Status = 'paused' |
| **Total Budget** | Currency | Sum of `daily_budget` × days |
| **Budget Utilization** | Percentage | `(total_spent / total_budget) × 100` |

---

### 2.2 Key Campaign Insights

**Function**: `get_brand_campaign_analytics()` → strategic report transformation  
**Display**: Insights cards with priority badges

#### Data Source

Strategic reports stored in `Campaign.metadata['report']`:

```python
# Get most recent custom campaign with strategic report
campaigns_with_reports = custom_campaigns.filter(
    metadata__report__isnull=False
).order_by('-created_at')

if campaigns_with_reports.exists():
    latest_campaign = campaigns_with_reports.first()
    strategic_report = latest_campaign.metadata['report']
    
    # Transform strategic findings to insights format
    campaign_insights = []
    for finding in strategic_report.get('strategic_findings', []):
        campaign_insights.append({
            'category': finding.get('finding', '')[:50],
            'insight': finding.get('finding', ''),
            'priority': finding.get('priority', 'medium'),  # high/medium/low
            'action_items': [finding.get('recommendation', '')]
        })
```

#### Strategic Report Structure

Generated by `generate_strategic_campaign_report()` in `analyst.py`:

```python
strategic_report = {
    'executive_summary': "...",
    'campaign_objective': "...",
    'key_metrics': {
        'communities_analyzed': 5,
        'discussions_reviewed': 78,
        'sentiment_score': 0.35,
        'top_themes': ['pricing', 'quality', 'customer_service']
    },
    'strategic_findings': [
        {
            'finding': "Primary competitor weakness in customer service response time",
            'evidence': "85% of competitor mentions cite slow support (avg 48hrs vs. industry 24hrs)",
            'recommendation': "Launch '24hr guarantee' campaign to capitalize on gap",
            'priority': 'high'
        },
        {
            'finding': "Emerging trend in sustainability concerns within target demographic",
            'evidence': "23% increase in 'eco-friendly' mentions month-over-month",
            'recommendation': "Develop sustainability messaging for Q1 product launch",
            'priority': 'medium'
        }
    ],
    'supporting_data': {
        'communities_analyzed': 5,
        'discussions_reviewed': 78,
        'sentiment_score': 0.35,
        'top_themes': ['pricing', 'quality', 'customer_service']
    },
    'next_steps': [
        "Conduct competitive analysis deep-dive",
        "Draft sustainability messaging framework",
        "Schedule stakeholder review meeting"
    ]
}
```

#### Display Format

**Insight Card**:
```
┌─────────────────────────────────────────────────┐
│ [HIGH]                                          │
│ Primary competitor weakness in customer service │
│                                                 │
│ Evidence: 85% of competitor mentions cite slow │
│ support (avg 48hrs vs. industry 24hrs)         │
│                                                 │
│ Recommendation:                                 │
│ • Launch '24hr guarantee' campaign             │
└─────────────────────────────────────────────────┘
```

**Priority Colors**:
- **HIGH**: Red badge, urgent action required
- **MEDIUM**: Yellow badge, important but not urgent
- **LOW**: Blue badge, monitor and plan

---

### 2.3 Strategic Report Generation

**Function**: `generate_strategic_campaign_report(campaign, brand, threads, pain_points, communities, influencers)`  
**Location**: `backend/agents/analyst.py`  
**LLM Model**: **gpt-4** (temperature=0.3, max_tokens=3000)

#### Report Components

1. **Executive Summary** (3-4 sentences):
   - Campaign overview
   - Key findings highlight
   - Overall strategic direction

2. **Campaign Objective** (verbatim from campaign):
   ```python
   campaign_objective = campaign.metadata.get('objectives', 'No objective specified.')
   ```

3. **Key Metrics**:
   ```python
   key_metrics = {
       'communities_analyzed': len(communities),
       'discussions_reviewed': len(threads),
       'sentiment_score': round(avg_sentiment, 2),
       'top_themes': top_themes[:5]
   }
   ```

4. **Strategic Findings** (3-5 findings):
   - Generated by GPT-4 analysis of campaign data
   - Each finding includes: finding, evidence, recommendation, priority
   - Aligned with campaign objectives

5. **Supporting Data**:
   - Quantitative backing for findings
   - Community statistics
   - Sentiment breakdown
   - Theme analysis

6. **Next Steps** (3-5 action items):
   - Prioritized by impact and feasibility
   - Specific and actionable
   - Time-bound where possible

#### LLM Prompt

```python
prompt = f"""
Analyze the following campaign data and generate a strategic report.

CAMPAIGN: {campaign.name}
OBJECTIVE: {campaign_objective}
BRAND: {brand.name}
INDUSTRY: {brand.industry}

DATA COLLECTED (3 months):
- Communities: {len(communities)} analyzed
- Discussions: {len(threads)} reviewed
- Pain Points: {len(pain_points)} identified
- Influencers: {len(influencers)} tracked

TOP PAIN POINTS:
{pain_points_summary}

TOP INFLUENCERS:
{influencers_summary}

TOP COMMUNITIES:
{communities_summary}

Generate a strategic report with:
1. Executive Summary (3-4 sentences)
2. 3-5 Strategic Findings (finding, evidence, recommendation, priority)
3. Recommended Next Steps (3-5 action items)

Focus on insights that directly support the campaign objective.
Provide specific, actionable recommendations with data-backed evidence.
"""

response = llm.invoke(prompt)
```

---

### 2.4 Report Export (PDF)

**Function**: `generate_strategic_report_pdf(campaign, brand)`  
**Location**: `backend/agents/analyst.py`  
**Library**: ReportLab

#### PDF Structure

```python
# Document setup
doc = SimpleDocTemplate(
    buffer,
    pagesize=letter,
    rightMargin=72,
    leftMargin=72,
    topMargin=72,
    bottomMargin=18
)

elements = []

# Title
elements.append(Paragraph("Strategic Campaign Report", title_style))

# Campaign Info Table
campaign_info = [
    ["Campaign:", campaign.name],
    ["Brand:", brand.name],
    ["Type:", campaign.campaign_type.upper()],
    ["Status:", campaign.status.upper()],
    ["Generated:", datetime.now().strftime("%B %d, %Y at %H:%M")]
]

# Executive Summary
elements.append(Paragraph("Executive Summary", heading_style))
elements.append(Paragraph(exec_summary, body_style))

# Campaign Objective
elements.append(Paragraph("Campaign Objective", heading_style))
elements.append(Paragraph(objective, body_style))

# Key Metrics Table
metrics_data = [['Metric', 'Value']]
for key, value in key_metrics.items():
    metric_name = key.replace('_', ' ').title()
    metrics_data.append([metric_name, str(value)])

# Strategic Findings (with priority colors)
for idx, finding in enumerate(strategic_findings, 1):
    priority = finding.get('priority', 'medium').upper()
    priority_color = {
        'HIGH': '#dc2626',
        'MEDIUM': '#f59e0b',
        'LOW': '#3b82f6'
    }.get(priority, '#6b7280')
    
    finding_title = f"{idx}. {finding.get('finding', 'No finding')}"
    elements.append(Paragraph(finding_title, subheading_style))
    
    priority_text = f"<font color='{priority_color}'><b>Priority: {priority}</b></font>"
    elements.append(Paragraph(priority_text, body_style))
    
    if finding.get('evidence'):
        evidence_text = f"<b>Evidence:</b> {finding.get('evidence')}"
        elements.append(Paragraph(evidence_text, body_style))
    
    if finding.get('recommendation'):
        rec_text = f"<b>Recommendation:</b> {finding.get('recommendation')}"
        elements.append(Paragraph(rec_text, body_style))

# Supporting Data Table
support_data_list = [
    ['Communities Analyzed', str(supporting_data.get('communities_analyzed', 0))],
    ['Discussions Reviewed', str(supporting_data.get('discussions_reviewed', 0))],
    ['Sentiment Score', f"{supporting_data.get('sentiment_score', 0):.2f}"],
    ['Key Themes', ', '.join(supporting_data.get('top_themes', []))]
]

# Next Steps
for idx, step in enumerate(next_steps, 1):
    step_text = f"{idx}. {step}"
    elements.append(Paragraph(step_text, body_style))

# Build PDF
doc.build(elements)
pdf_content = buffer.getvalue()
```

#### Download Endpoint

```python
@api_view(['GET'])
def download_campaign_report_pdf(request, campaign_id):
    campaign = Campaign.objects.get(id=campaign_id)
    brand = campaign.brand
    
    pdf_bytes = generate_strategic_report_pdf(campaign, brand)
    
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="campaign_report_{campaign.name}_{datetime.now().strftime("%Y%m%d")}.pdf"'
    
    return response
```

**Usage**: `GET /api/v1/campaigns/{campaign_id}/report/pdf/`

---

## Summary

### Brand Analytics Dashboard
- **Purpose**: Long-term brand monitoring (6 months)
- **Focus**: Community health, pain point trends, influencer identification
- **Key Metrics**: Echo scores, positivity ratio, mention volume
- **AI Insights**: o3-mini powered strategic analysis

### Campaign Analytics Dashboard
- **Purpose**: Strategic campaign planning (3 months)
- **Focus**: Objective-driven insights, competitive analysis
- **Key Output**: Strategic reports with priority findings
- **Export**: PDF reports for stakeholder sharing

### Data Flow
1. **Scout Agent** collects data via Tavily Search API
2. **Cleaner Agent** validates and sanitizes content
3. **Analyst Agent** generates insights and reports
4. **Dashboard** displays calculated metrics and visualizations
5. **AI Layer** synthesizes insights from all data sources

---

**Version**: 2.0  
**Last Updated**: November 6, 2025  
**Status**: Production Ready ✅
