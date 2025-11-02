# Dashboard KPI Cards Enhancement - Complete

## Issue
Dashboard KPI cards were showing zeros despite successful data collection by Celery tasks. The Celery logs confirmed that Brand Analytics campaigns were collecting communities, pain points, and threads, but the dashboard displayed no metrics.

## Root Cause
The `get_brand_dashboard_kpis()` function in `backend/api/views.py` was filtering automatic campaigns with `status='active'`:

```python
automatic_campaign = Campaign.objects.filter(
    brand_id=brand_id,
    campaign_type='automatic',
    status='active'  # ❌ Problem: Nike was 'completed', Yamaha was 'paused'
).first()
```

Both existing campaigns had different statuses:
- **Nike - Brand Analytics**: `status='completed'`
- **Yamaha XSR 155 - Brand Analytics**: `status='paused'`

This caused the function to return `None` for the automatic campaign, resulting in all KPI values being zero.

## Solution

### 1. Backend Fix (backend/api/views.py)

**Changed the campaign query** (lines ~856-860):
```python
# ✅ FIX: Get automatic campaign only (Brand Analytics)
# Note: We don't filter by status because we want to show KPIs even for completed/paused campaigns
automatic_campaign = Campaign.objects.filter(
    brand_id=brand_id,
    campaign_type='automatic'
).first()
```

**Updated active campaigns count** (lines ~875-879):
```python
# Count active campaigns (active or running status)
active_campaigns_count = Campaign.objects.filter(
    brand_id=brand_id,
    campaign_type='automatic',
    status__in=['active', 'running']
).count()
```

This allows the dashboard to:
- Display KPI metrics from **any** automatic campaign (regardless of status)
- Show accurate "Active Campaigns" count (only campaigns with status='active' or 'running')
- Maintain historical data visibility for completed campaigns

### 2. Frontend Enhancement (frontend/src/components/Dashboard.tsx)

**Enhanced KPI cards with:**

1. **Visual improvements:**
   - Color-coded gradient backgrounds (blue, purple, amber, green)
   - Icon indicators for each metric (Activity, Users, AlertCircle, Heart)
   - Larger, more prominent numbers (text-3xl)
   - Better typography and spacing

2. **Trend indicators:**
   - Show percentage changes with arrows (TrendingUp/TrendingDown)
   - High-Echo Communities: change vs last week
   - Pain Points: change vs last month
   - Positivity Ratio: percentage point change vs last week
   - Color-coded trends (green for positive, red for negative)

3. **Additional context:**
   - "Automatic Brand Analytics" label on Active Campaigns
   - "Echo Score ≥ 7.0" note on High-Echo Communities
   - "Growth > 50%" note on New Pain Points
   - Positive/Negative sentiment breakdown on Positivity Ratio

4. **LLM Usage & Cost Tracking:**
   - New section below KPI cards (only shows if data exists)
   - Token usage card: Shows tokens processed (in thousands) over last 7 days
   - Cost card: Shows actual OpenAI API cost in USD (3 decimal precision)
   - Indigo and emerald color schemes for differentiation

**Added icons:**
```tsx
import { Activity, AlertCircle, Heart } from 'lucide-react';
```

## Test Results

### Nike Brand (ID: 8bef0e7b-25ed-488d-ae65-ed9576e2ad51)
```
✅ Active Campaigns: 0 (campaign is completed)
✅ High-Echo Communities: 2 (from 11 total communities)
✅ New Pain Points: 0 (no new keywords with >50% growth in current month)
✅ Positivity Ratio: 80.0% (from sentiment score -0.080)
✅ LLM Cost: $0.0046 (from 15 threads)
```

### Yamaha XSR 155 (ID: 542ae05b-97bc-4b1b-9e14-a0d667a6c206)
```
✅ Active Campaigns: 0 (campaign is paused)
✅ High-Echo Communities: 5 (from 6 total communities)
✅ New Pain Points: 0 (no new keywords with >50% growth in current month)
✅ Positivity Ratio: 78.3% (from sentiment score 0.048)
✅ LLM Cost: $0.003 (from 10 threads)
```

### API Response Verification
Both brands now return correct KPI data:
```bash
curl "http://localhost:8000/api/v1/dashboard/overview/brand/?brand_id=<BRAND_ID>"
```

Returns proper KPI object with all metrics populated.

## Data Flow Confirmed

1. **Celery Task** (`scout_brand_analytics_task`):
   - Collects threads from Reddit, social media, forums
   - Creates Community, PainPoint, Thread records
   - Links all records to automatic campaign via `campaign` foreign key

2. **Celery Task** (`update_dashboard_metrics_task`):
   - Calculates aggregated metrics for campaigns
   - Updates Campaign model fields

3. **Backend API** (`/api/v1/dashboard/overview/brand/`):
   - Queries automatic campaign (now works for any status)
   - Calculates KPIs from Community, PainPoint, Thread models
   - Returns structured KPI object

4. **Frontend Dashboard**:
   - Fetches data from API on load and brand selection
   - Displays KPIs in enhanced cards with trends
   - Shows LLM usage/cost when available

## Files Modified

1. **backend/api/views.py**
   - Line ~856-860: Removed `status='active'` filter
   - Line ~875-879: Added proper active campaigns count

2. **frontend/src/components/Dashboard.tsx**
   - Line 4: Added Activity, AlertCircle, Heart icons
   - Lines 618-730: Enhanced all 4 KPI cards with gradients, trends, context
   - Lines 733-768: Added LLM usage & cost tracking section

3. **backend/debug_kpis.py** (created for debugging)
   - Comprehensive debug script for KPI troubleshooting
   - Can be run with: `python manage.py shell < debug_kpis.py`

## Metrics Explanation

### Active Campaigns
- Shows count of automatic campaigns with `status='active'` or `status='running'`
- May show 0 if campaigns are completed/paused (normal behavior)

### High-Echo Communities
- Communities with `echo_score >= 7.0`
- Indicates strong echo chambers where brand discussions resonate
- Change calculated vs last week

### New Pain Points
- Keywords with `growth_percentage > 50%` in most recent completed month
- Excludes current incomplete month to avoid skewed data
- Change calculated vs previous month

### Positivity Ratio
- Calculated from sentiment scores (-1 to +1 range)
- Converted to percentage: `(sentiment + 1) * 50`
- Shows positive/negative breakdown
- Change calculated vs last week (percentage points)

### LLM Usage (Last 7 Days)
- Total tokens processed by AI agents
- Displayed in thousands (K)
- Sourced from Thread model `token_count` field

### LLM Cost (Last 7 Days)
- Total OpenAI API cost in USD
- Sourced from Thread model `processing_cost` field
- Shows 3 decimal precision for accuracy

## Status
✅ **COMPLETE** - Dashboard KPI cards now display real metrics from automatic campaigns regardless of campaign status. Enhanced UI provides better visibility with trends, context, and cost tracking.
