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
]