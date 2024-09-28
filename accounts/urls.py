from django.urls import path
from .views import register, login  # Import both register and login views

urlpatterns = [
    path('api/register/', register, name='register'),
    path('api/login/', login, name='login'),  # Ensure login view is imported
]
