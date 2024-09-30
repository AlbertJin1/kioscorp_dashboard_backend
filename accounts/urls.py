from django.urls import path
from .views import (
    register,
    register_owner,
    login,
    update_profile,
    get_users,
    delete_user,
    update_user,
    get_user_by_id,
)

urlpatterns = [
    path('api/register/', register, name='register'),
    path('api/register-owner/', register_owner, name='register_owner'),
    path('api/login/', login, name='login'),
    path('api/profile/', update_profile, name='update_profile'),
    path('api/users/', get_users, name='get_users'),
    path('api/users/<int:user_id>/', get_user_by_id,
         name='get_user_by_id'),  # Fetch user by ID
    path('api/users/<int:user_id>/delete/', delete_user,
         name='delete_user'),  # Delete user by ID
    path('api/users/<int:user_id>/update/', update_user,
         name='update_user'),  # Update user by ID
]
