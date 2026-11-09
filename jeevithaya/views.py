from django.shortcuts import render

def login(request):
    return render(request, 'login.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def donors(request):
    return render(request, 'donors.html')

def patients(request):
    return render(request, 'patients.html')

def requests_page(request):
    return render(request, 'requests.html')

def inventory(request):
    return render(request, 'inventory.html')

def donation(request):
    return render(request, 'donation.html')

def verification(request):
    return render(request, 'verification.html')

def disposal(request):
    return render(request, 'disposal.html')

def reports(request):
    return render(request, 'reports.html')

def create_user(request):
    return render(request, 'create_user.html')

def profile(request):
    return render(request, 'profile.html')

def index(request):
    return render(request, 'index.html')

def logout(request):
    return render(request, 'logout.html')

def presentation(request):
    return render(request, 'presentation.html')