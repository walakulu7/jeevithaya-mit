from django.urls import path
from . import views

urlpatterns = [
    # Auth API
    path('auth/login/', views.api_auth_login, name='api_auth_login'),
    path('auth/logout/', views.api_auth_logout, name='api_auth_logout'),
    path('auth/me/', views.api_auth_me, name='api_auth_me'),

    # User API
    path('users/', views.api_users, name='api_users'),
    path('users/<int:user_id>/', views.api_user_detail, name='api_user_detail'),
    
    # Donor API
    path('donors/', views.api_donors, name='api_donors'),
    path('donors/<str:donor_id>/', views.api_donor_detail, name='api_donor_detail'),
    
    # Patient API
    path('patients/', views.api_patients, name='api_patients'),
    path('patients/<str:patient_id>/', views.api_patient_detail, name='api_patient_detail'),
    
    # Blood Request API
    path('requests/', views.api_requests, name='api_requests'),
    path('requests/<str:request_id>/', views.api_request_detail, name='api_request_detail'),
    
    # Donation API
    path('donations/', views.api_donations, name='api_donations'),
    path('donations/<str:donation_id>/', views.api_donation_detail, name='api_donation_detail'),
    
    # Inventory API
    path('inventory/', views.api_inventory, name='api_inventory'),
    path('inventory/<str:unit_id>/', views.api_inventory_detail, name='api_inventory_detail'),
    
    # Verification API
    path('verifications/', views.api_verifications, name='api_verifications'),
    path('verifications/<str:verification_id>/', views.api_verification_detail, name='api_verification_detail'),
    
    # Disposal API
    path('disposals/', views.api_disposals, name='api_disposals'),
    path('disposals/<str:disposal_id>/', views.api_disposal_detail, name='api_disposal_detail'),
    
    # Dashboard Stats
    path('dashboard/stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
]
