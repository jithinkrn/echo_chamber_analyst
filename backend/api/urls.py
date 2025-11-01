"""
API URLs for EchoChamber Analyst.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_root, name='api_root'),
    path('health/', views.health_check, name='health_check'),

    # LangGraph workflow endpoints
    path('chat/', views.chat_query, name='chat_query'),
    path('search/', views.search_content, name='search_content'),
    path('campaigns/<uuid:campaign_id>/summary/', views.campaign_summary, name='campaign_summary'),
    path('workflows/content-analysis/', views.start_content_analysis, name='start_content_analysis'),
    path('workflows/<str:workflow_id>/status/', views.workflow_status, name='workflow_status'),
    
    # Dashboard endpoints
    path('dashboard/overview/', views.dashboard_overview, name='dashboard_overview'),
    path('dashboard/overview/brand/', views.dashboard_overview_brand_filtered, name='dashboard_overview_brand_filtered'),
    path('threads/<str:thread_id>/', views.thread_detail, name='thread_detail'),
    
    # Brand management endpoints
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/<uuid:brand_id>/', views.brand_detail, name='brand_detail'),
    path('brands/<uuid:brand_id>/competitors/', views.competitor_list, name='competitor_list'),

    path('brands/new/', views.create_brand, name='create_brand'),
    path('brands/<uuid:brand_id>/analysis/', views.control_brand_analysis, name='control_brand_analysis'),
    path('scout/analyze/', views.trigger_scout_analysis, name='trigger_scout_analysis'),

    # Scout and data endpoints
    path('brands/<uuid:brand_id>/scout-results/', views.get_scout_results, name='get_scout_results'),
    path('brands/<uuid:brand_id>/influencers/', views.get_brand_influencers, name='get_brand_influencers'),
    path('brands/<uuid:brand_id>/analysis-summary/', views.get_brand_analysis_summary, name='get_brand_analysis_summary'),
    path('communities/', views.get_communities, name='get_communities'),
    
    # Community detail endpoints
    path('community/<uuid:community_id>/pain-points/', views.get_community_pain_points, name='get_community_pain_points'),
    path('community/<uuid:community_id>/threads/', views.get_community_threads, name='get_community_threads'),
    path('community/<uuid:community_id>/influencers/', views.get_community_influencers, name='get_community_influencers'),
    
    path('pain-points/', views.get_pain_points, name='get_pain_points'),
    path('threads/', views.get_threads, name='get_threads'),
    
    # Campaign management endpoints
    path('campaigns/', views.get_campaigns, name='get_campaigns'),  # GET = list, POST = create
    path('campaigns/<uuid:campaign_id>/', views.get_campaign_detail, name='get_campaign_detail'),
    path('campaigns/<uuid:campaign_id>/report/', views.get_campaign_strategic_report, name='get_campaign_strategic_report'),
    path('campaigns/<uuid:campaign_id>/report/pdf/', views.download_campaign_report_pdf, name='download_campaign_report_pdf'),
    path('brands/<uuid:brand_id>/campaigns/', views.list_custom_campaigns_for_brand, name='list_custom_campaigns_for_brand'),
    path('brands/<uuid:brand_id>/campaigns/<uuid:campaign_id>/analytics/', views.get_specific_campaign_analytics, name='get_specific_campaign_analytics'),

    # Task Management and Monitoring Endpoints
    path('tasks/scout/', views.trigger_scout_task, name='trigger_scout_task'),
    path('tasks/insights/', views.trigger_insights_task, name='trigger_insights_task'),
    path('tasks/cleanup/', views.trigger_cleanup_task, name='trigger_cleanup_task'),
    path('tasks/workflow/', views.trigger_workflow_task, name='trigger_workflow_task'),
    path('tasks/<str:task_id>/status/', views.task_status, name='task_status'),

    # Monitoring Endpoints
    path('monitoring/dashboard/', views.monitoring_dashboard, name='monitoring_dashboard'),
    path('monitoring/workflows/metrics/', views.workflow_metrics, name='workflow_metrics'),
    path('monitoring/agents/health/', views.agent_health, name='agent_health'),
    path('monitoring/agents/<str:agent_name>/restart/', views.restart_agent, name='restart_agent'),

    # Source Management Endpoints
    path('sources/', views.get_all_sources, name='get_all_sources'),
    path('sources/custom/', views.create_custom_source, name='create_custom_source'),
    path('sources/custom/<uuid:source_id>/', views.delete_custom_source, name='delete_custom_source'),

    # System Settings Endpoint
    path('settings/', views.system_settings, name='system_settings'),

    # LLM Source Discovery Endpoints
    path('discovered-sources/', views.get_discovered_sources, name='get_discovered_sources'),
    path('discover-sources/', views.discover_sources_api, name='discover_sources_api'),
]