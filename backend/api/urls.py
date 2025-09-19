"""
API URLs for EchoChamber Analyst.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_root, name='api_root'),

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
]