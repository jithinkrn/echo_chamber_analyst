# Architecture Separation Implementation Progress

## ✅ COMPLETED PHASES

### Phase 1: Database Schema Changes ✅ COMPLETE

**Changes Made:**

1. **Campaign Model** (`backend/common/models.py:84-133`)
   - ✅ Added `campaign_type` field with choices: 'automatic' or 'custom'
   - Default: 'custom'

2. **Community Model** (`backend/common/models.py:444-500`)
   - ✅ Added `brand` FK (nullable)
   - ✅ Added `campaign` FK (nullable)
   - ✅ Updated `unique_together` to include campaign

3. **PainPoint Model** (`backend/common/models.py:503-547`)
   - ✅ Added `brand` FK (nullable)

4. **Thread Model** (`backend/common/models.py:550-594`)
   - ✅ Added `brand` FK (nullable)

5. **Migrations**
   - ✅ Generated migration file: `common/migrations/0011_alter_community_unique_together_and_more.py`

### Phase 2: Separate Data Collection ✅ COMPLETE

**New Celery Tasks Created:**

1. **scout_brand_analytics_task()** (`backend/agents/tasks.py:727-835`)
   - Collects data for Brand Analytics (automatic campaigns)
   - Filters by `campaign_type='automatic'`
   - Uses brand keywords and comprehensive monitoring
   - Calls `store_brand_analytics_data()`

2. **scout_custom_campaign_task()** (`backend/agents/tasks.py:838-950`)
   - Collects data for Custom Campaigns
   - Filters by `campaign_type='custom'`
   - Uses campaign-specific keywords, sources, objectives
   - **Includes campaign objectives (from description field)** in scout_config
   - Calls `store_custom_campaign_data()`

3. **Updated check_and_execute_scheduled_campaigns()** (`backend/agents/tasks.py:694-702`)
   - Routes to appropriate task based on campaign type
   - Automatic campaigns → scout_brand_analytics_task
   - Custom campaigns → scout_custom_campaign_task

**New Storage Functions Created:**

1. **store_brand_analytics_data()** (`backend/agents/nodes.py:610-764`)
   - Stores data for Brand Analytics ONLY
   - Links all data (communities, pain points, threads, influencers) to:
     - brand FK
     - automatic_campaign FK
   - Generates Brand Analytics insights via `_generate_and_store_brand_analytics_insights()`

2. **store_custom_campaign_data()** (`backend/agents/nodes.py:767-930`)
   - Stores data for Custom Campaigns ONLY
   - Links all data to:
     - brand FK
     - custom_campaign FK
   - **Stores campaign objectives in metadata**
   - Generates Custom Campaign insights via `_generate_and_store_custom_campaign_insights()`

**New Insight Generation Functions:**

1. **_generate_and_store_brand_analytics_insights()** (`backend/agents/nodes.py:291-344`)
   - Generates AI-Powered Key Insights (6 simple strings)
   - Uses Analytics Agent: `generate_ai_powered_insights_from_brand_analytics()`
   - Stores in `campaign.metadata['ai_insights']`

2. **_generate_and_store_custom_campaign_insights()** (`backend/agents/nodes.py:347-409`)
   - Generates Custom Campaign insights (structured objects)
   - Uses Analytics Agent: `generate_campaign_ai_insights()`
   - **Considers campaign objectives from description**
   - Stores in `campaign.metadata['insights']`
   - Stores objectives in `campaign.metadata['objectives']`

---

## ✅ COMPLETED PHASES (CONTINUED)

### Phase 3: API Query Updates ✅ COMPLETE

**Files Updated:**

1. **get_brand_dashboard_kpis()** - `backend/api/views.py:833` ✅
   - Filters by automatic campaign only
   - Filters communities by brand + automatic campaign
   - Filters pain points by brand + automatic campaign
   - Filters threads by brand + automatic campaign
   - Returns zero metrics if no automatic campaign exists

2. **get_brand_top_pain_points()** - `backend/api/views.py:952` ✅
   - Filters by brand + automatic campaign only
   - Returns empty array if no automatic campaign

3. **get_brand_community_watchlist()** - `backend/api/views.py:1155` ✅
   - Filters by brand + automatic campaign
   - Returns empty array if no automatic campaign

4. **get_brand_heatmap_data()** - `backend/api/views.py:982` ✅
   - Filters by brand + automatic campaign
   - Returns empty structure if no automatic campaign

5. **get_brand_influencer_pulse()** - `backend/api/views.py:1210` ✅
   - Filters by brand + automatic campaign
   - Returns empty array if no automatic campaign

6. **get_brand_analysis_summary()** - `backend/api/views.py:2079` ✅
   - Uses automatic campaign only
   - Retrieves stored `ai_insights` from campaign metadata
   - Falls back to generating new insights if not stored

7. **get_brand_campaign_analytics()** - `backend/api/views.py:1247` ✅
   - Filters by custom campaigns ONLY (`campaign_type='custom'`)
   - Excludes automatic campaigns completely

8. **control_brand_analysis()** - `backend/api/views.py:1598` ✅
   - Sets `campaign_type='automatic'` when creating campaign
   - Uses `scout_brand_analytics_task` instead of `scout_reddit_task`

9. **get_campaign_detail()** - `backend/api/views.py:2527` ✅
   - Routes to appropriate task based on campaign type
   - Automatic campaigns → `scout_brand_analytics_task`
   - Custom campaigns → `scout_custom_campaign_task`

---

## ✅ COMPLETED PHASES (CONTINUED)

### Phase 4: Data Migration ✅ COMPLETE

**Migration Script Created:** `backend/common/management/commands/migrate_campaign_separation.py`

The script migrates existing data in 5 steps:
1. Marks automatic campaigns with `campaign_type='automatic'`
2. Marks custom campaigns with `campaign_type='custom'`
3. Links communities to brands via campaigns
4. Links pain points to brands
5. Links threads to brands

**Usage:**
```bash
# Dry run (preview changes without saving)
python manage.py migrate_campaign_separation --dry-run

# Apply migration
python manage.py migrate_campaign_separation
```

**Features:**
- Transaction-safe (rolls back on error)
- Dry-run mode for testing
- Detailed progress logging
- Verification summary

---

## 📋 IMPLEMENTATION CHECKLIST

### Database
- [x] Add campaign_type field to Campaign
- [x] Add brand FK to Community
- [x] Add campaign FK to Community
- [x] Add brand FK to PainPoint
- [x] Add brand FK to Thread
- [x] Generate Django migrations

### Data Collection
- [x] Create scout_brand_analytics_task
- [x] Create scout_custom_campaign_task
- [x] Create store_brand_analytics_data function
- [x] Create store_custom_campaign_data function
- [x] Include campaign objectives in custom campaign collection
- [x] Update check_and_execute_scheduled_campaigns
- [x] Create brand analytics insight generation
- [x] Create custom campaign insight generation

### API Endpoints
- [x] Update get_brand_dashboard_kpis
- [x] Update get_brand_top_pain_points
- [x] Update get_brand_community_watchlist
- [x] Update get_brand_heatmap_data
- [x] Update get_brand_influencer_pulse
- [x] Update get_brand_analysis_summary
- [x] Update get_brand_campaign_analytics
- [x] Update control_brand_analysis
- [x] Verify get_campaign_detail updates

### Data Migration
- [x] Create migration script
- [ ] Run migration on existing data (USER ACTION REQUIRED)
- [ ] Verify data separation (USER ACTION REQUIRED)

### Testing
- [ ] Apply Django migrations (USER ACTION REQUIRED)
- [ ] Run data migration script (USER ACTION REQUIRED)
- [ ] Test Brand Analytics data collection (USER ACTION REQUIRED)
- [ ] Test Custom Campaign data collection (USER ACTION REQUIRED)
- [ ] Test dashboard displays correct data (USER ACTION REQUIRED)
- [ ] Test insights generation (USER ACTION REQUIRED)
- [ ] Verify no data mixing (USER ACTION REQUIRED)

---

## Key Design Decisions

### 1. Campaign Objectives Handling (Custom Campaigns Only)
- Campaign objectives are stored in `Campaign.description` field
- Passed to scout agent via `scout_config['campaign_objectives']`
- Stored in `campaign.metadata['objectives']`
- Used by Analytics Agent when generating custom campaign insights

### 2. Data Separation Strategy
- Same models (Community, PainPoint, Thread) used for both types
- Separation achieved through:
  - `Campaign.campaign_type` field ('automatic' vs 'custom')
  - `brand` FK on all models
  - `campaign` FK on all models
- Queries filter by campaign_type to separate data

### 3. Insight Types
- **Brand Analytics** → `ai_insights` (6 simple strings)
- **Custom Campaigns** → `insights` (structured objects with category, priority, action_items)

### 4. Task Routing
- Scheduler checks `campaign.campaign_type`
- Routes to appropriate task automatically
- No manual intervention needed

---

## Next Steps

1. Complete Phase 3: Update all API queries
2. Complete Phase 4: Create and run data migration
3. Test end-to-end functionality
4. Verify complete separation

---

**Status**: ✅ **ALL 4 PHASES COMPLETE!** | Ready for Testing

## 🎉 Implementation Summary

**✅ COMPLETED:**
- Phase 1: Database schema changes (4 model updates + migration)
- Phase 2: Separate data collection tasks and storage functions
- Phase 3: Updated 9 API endpoints to filter by campaign type
- Phase 4: Created data migration script

**📋 NEXT STEPS FOR USER:**

1. **Apply Django Migration:**
   ```bash
   cd backend
   python manage.py migrate
   ```

2. **Run Data Migration (Dry Run First):**
   ```bash
   python manage.py migrate_campaign_separation --dry-run
   ```

3. **Apply Data Migration:**
   ```bash
   python manage.py migrate_campaign_separation
   ```

4. **Restart Services:**
   ```bash
   # Restart Django server
   # Restart Celery worker
   # Restart Celery beat
   ```

5. **Test Complete Separation:**
   - Click "Start Analytics" for a brand → Should run Brand Analytics (automatic campaign)
   - Create a Custom Campaign → Should collect separate data
   - Check Brand Analytics dashboard → Should show only automatic campaign data
   - Check Campaign Analytics section → Should show only custom campaign insights
