from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    register,
    register_owner,
    login,
    logout,
    change_password,
    update_profile,
    get_users,
    delete_user,
    update_user,
    get_user_by_id,
    add_user,
    LogView,
    MainCategoryView,
    SubCategoryView,
    ProductView,
    ProductDetailView,
)

urlpatterns = [
    path("api/register/", register, name="register"),
    path("api/register-owner/", register_owner, name="register_owner"),
    path("api/login/", login, name="login"),
    # Ensure this matches the request
    path("api/logout/", logout, name="logout"),
    path("api/profile/", update_profile, name="update_profile"),
    path("api/change-password/", change_password, name="change_password"),
    path("api/users/", get_users, name="get_users"),
    # New endpoint for adding a user
    path("api/users/add/", add_user, name="add_user"),
    path("api/users/<int:user_id>/", get_user_by_id, name="get_user_by_id"),
    path("api/users/<int:user_id>/delete/", delete_user, name="delete_user"),
    path("api/users/<int:user_id>/update/", update_user, name="update_user"),
    path("logs/", LogView.as_view(), name="logs"),  # Added name for logs view
    path("api/main-categories/", MainCategoryView.as_view(), name="main_categories"),
    path("api/sub-categories/", SubCategoryView.as_view(), name="sub_categories"),
    path("api/products/", ProductView.as_view(), name="products"),
    path(
        "api/products/<int:product_id>/",
        ProductDetailView.as_view(),
        name="product_detail",
    ),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
