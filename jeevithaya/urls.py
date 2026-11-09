"""
URL configuration for jeevithaya project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('bloodbank.urls')),
    path('', views.login, name='login'),
    path('login.html', views.login, name='login_html'),
    path('dashboard.html', views.dashboard, name='dashboard'),
    path('donors.html', views.donors, name='donors'),
    path('patients.html', views.patients, name='patients'),
    path('requests.html', views.requests_page, name='requests'),
    path('inventory.html', views.inventory, name='inventory'),
    path('donation.html', views.donation, name='donation'),
    path('verification.html', views.verification, name='verification'),
    path('disposal.html', views.disposal, name='disposal'),
    path('reports.html', views.reports, name='reports'),
    path('create_user.html', views.create_user, name='create_user'),
    path('profile.html', views.profile, name='profile'),
    path('index.html', views.index, name='index'),
    path('logout.html', views.logout, name='logout'),
    path('presentation.html', views.presentation, name='presentation'),
]
