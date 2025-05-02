"""
URL patterns for the s3_connector app
"""
from django.urls import path
from . import views

app_name = 's3_connector'

urlpatterns = [
    # Main data API endpoints
    path('api/combined-metrics/', views.combined_metrics, name='combined_metrics'),
    path('api/financial-summary/', views.financial_summary, name='financial_summary'),
    
    # Client-specific endpoints
    path('api/clients/', views.client_list, name='client_list'),
    path('api/clients/<str:client_name>/', views.client_detail, name='client_detail'),
    
    # Industry analysis
    path('api/industries/', views.industry_summary, name='industry_summary'),
    
    # Utility endpoints
    path('api/test-connection/', views.test_connection, name='test_connection'),
]