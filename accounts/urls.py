from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    # User management
    register,
    register_owner,
    login,
    logout,
    change_password,
    update_profile,
    get_users,
    add_user,
    get_user_by_id,
    update_user,
    delete_user,
    reset_password,
    update_profile_picture,
    get_profile_picture,
    get_profile_picture_admin,
    # Logs
    LogView,
    # Categories
    MainCategoryView,
    SubCategoryView,
    delete_subcategory_image,
    # Products
    ProductView,
    ProductDetailView,
    low_selling_products,
    # Orders
    create_order,
    pay_order,
    order_counts,
    PendingOrdersView,
    VoidOrderView,
    order_history,
    # Sales
    get_sales_data,
    monthly_sales,
    sales_by_category,
    satisfaction_overview,
    CustomerCountByMonthView,
    # Feedback
    FeedbackCreateView,
    # Miscellaneous
    validate_session,
    print_receipt,
)

urlpatterns = [
    # User authentication
    path("api/validate-session/", validate_session, name="validate_session"),
    path("api/register/", register, name="register"),
    path("api/register-owner/", register_owner, name="register_owner"),
    path("api/login/", login, name="login"),
    path("api/logout/", logout, name="logout"),
    path("api/reset-password/", reset_password, name="reset_password"),
    # User profile
    path("api/profile/", update_profile, name="update_profile"),
    path("api/change-password/", change_password, name="change_password"),
    path("api/users/", get_users, name="get_users"),
    path("api/users/add/", add_user, name="add_user"),
    path("api/users/<int:user_id>/", get_user_by_id, name="get_user_by_id"),
    path("api/users/<int:user_id>/delete/", delete_user, name="delete_user"),
    path("api/users/<int:user_id>/update/", update_user, name="update_user"),
    path(
        "api/update-profile-picture/",
        update_profile_picture,
        name="update_profile_picture",
    ),
    path("api/profile-picture/", get_profile_picture, name="get_profile_picture"),
    path(
        "api/users/<int:user_id>/profile-picture/",
        get_profile_picture_admin,
        name="get_profile_picture_admin",
    ),
    # Logs
    path("logs/", LogView.as_view(), name="logs"),
    # Categories
    path("api/main-categories/", MainCategoryView.as_view(), name="main_categories"),
    path("api/sub-categories/", SubCategoryView.as_view(), name="sub_categories"),
    path(
        "api/sub-categories/<int:sub_category_id>/",
        SubCategoryView.as_view(),
        name="sub_category_detail",
    ),
    path(
        "api/sub-categories/<int:sub_category_id>/delete-image/",
        delete_subcategory_image,
        name="delete_subcategory_image",
    ),
    # Products
    path("api/products/", ProductView.as_view(), name="products"),
    path(
        "api/products/<int:product_id>/",
        ProductDetailView.as_view(),
        name="product_detail",
    ),
    path(
        "api/low-selling-products/", low_selling_products, name="low-selling-products"
    ),
    # Orders
    path("api/orders/pending/", PendingOrdersView.as_view(), name="pending-orders"),
    path("api/orders/void/<int:order_id>/", VoidOrderView.as_view(), name="void-order"),
    path("api/create-order/", create_order, name="create_order"),
    path("api/orders/pay/<int:order_id>/", pay_order, name="pay_order"),
    path("api/orders/counts/", order_counts, name="order_counts"),
    path("api/orders/history/", order_history, name="order_history"),
    # Sales
    path("api/sales/data/", get_sales_data, name="sales_data"),
    path("api/sales/monthly/", monthly_sales, name="monthly_sales"),
    path("api/sales/category/", sales_by_category, name="sales_by_category"),
    # Feedback
    path("api/feedback/", FeedbackCreateView.as_view(), name="feedback-create"),
    path(
        "api/feedback/satisfaction/",
        satisfaction_overview,
        name="satisfaction_overview",
    ),
    # Miscellaneous
    path("api/print-receipt/", print_receipt, name="print_receipt"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
