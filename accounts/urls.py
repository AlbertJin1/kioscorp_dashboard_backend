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
    update_profile_picture,
    get_profile_picture,
    print_receipt,
    validate_session,
    get_profile_picture_admin,
    FeedbackCreateView,
    PendingOrdersView,
    VoidOrderView,
    reset_password,
    create_order,
    pay_order,
    order_counts,
    satisfaction_overview,
    CustomerCountByMonthView,
    get_sales_data,
    order_history,
    monthly_sales,
    sales_by_category,
    low_selling_products,  # Import the low selling products view
)
from . import views

urlpatterns = [
    path("api/validate-session/", validate_session, name="validate_session"),
    path("api/register/", register, name="register"),
    path("api/register-owner/", register_owner, name="register_owner"),
    path("api/login/", login, name="login"),
    path("api/logout/", logout, name="logout"),
    path("api/profile/", update_profile, name="update_profile"),
    path("api/change-password/", change_password, name="change_password"),
    path("api/users/", get_users, name="get_users"),
    path("api/users/add/", add_user, name="add_user"),
    path("api/users/<int:user_id>/", get_user_by_id, name="get_user_by_id"),
    path("api/users/<int:user_id>/delete/", delete_user, name="delete_user"),
    path("api/users/<int:user_id>/update/", update_user, name="update_user"),
    path("logs/", LogView.as_view(), name="logs"),
    path("api/main-categories/", MainCategoryView.as_view(), name="main_categories"),
    path("api/sub-categories/", SubCategoryView.as_view(), name="sub_categories"),
    path(
        "api/sub-categories/<int:sub_category_id>/",
        SubCategoryView.as_view(),
        name="sub_category_detail",
    ),
    path("api/products/", ProductView.as_view(), name="products"),
    path(
        "api/products/<int:product_id>/",
        ProductDetailView.as_view(),
        name="product_detail",
    ),
    path(
        "api/update-profile-picture/",
        update_profile_picture,
        name="update_profile_picture",
    ),
    path("api/profile-picture/", get_profile_picture, name="get_profile_picture"),
    path("api/print-receipt/", print_receipt, name="print_receipt"),
    path(
        "api/users/<int:user_id>/profile-picture/",
        get_profile_picture_admin,
        name="get_profile_picture_admin",
    ),
    path("api/feedback/", FeedbackCreateView.as_view(), name="feedback-create"),
    path("api/orders/pending/", PendingOrdersView.as_view(), name="pending-orders"),
    path("api/orders/void/<int:order_id>/", VoidOrderView.as_view(), name="void-order"),
    path("api/reset-password/", reset_password, name="reset_password"),
    path("api/create-order/", create_order, name="create_order"),
    path("api/orders/pay/<int:order_id>/", pay_order, name="pay_order"),
    path("api/orders/counts/", order_counts, name="order_counts"),
    path(
        "api/feedback/satisfaction/",
        satisfaction_overview,
        name="satisfaction_overview",
    ),
    path(
        "api/customers/counts/month/",
        CustomerCountByMonthView.as_view(),
        name="customer_counts_by_month",
    ),
    path(
        "api/top-selling-products/",
        views.top_selling_products,
        name="top-selling-products",
    ),
    path(
        "api/low-selling-products/", low_selling_products, name="low-selling-products"
    ),  # New endpoint for low selling products
    path("api/sales/data/", get_sales_data, name="sales_data"),
    path("api/orders/history/", order_history, name="order_history"),
    path("api/sales/monthly/", monthly_sales, name="monthly_sales"),
    path("api/sales/category/", sales_by_category, name="sales_by_category"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
