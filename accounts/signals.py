from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import MainCategory, VATSetting
from django.contrib.auth import get_user_model


@receiver(post_migrate)
def create_default_main_categories(sender, **kwargs):
    if kwargs["app_config"].name == "accounts":
        main_categories = [
            {"main_category_name": "Auto Supply"},
            {"main_category_name": "Bolts"},
        ]

        for category in main_categories:
            MainCategory.objects.get_or_create(
                main_category_name=category["main_category_name"]
            )


@receiver(post_migrate)
def create_default_owner(sender, **kwargs):
    User = get_user_model()  # Get the custom user model
    if (
        kwargs["app_config"].name == "accounts"
    ):  # Ensure this runs only for the accounts app
        # Check if the owner user already exists
        if not User.objects.filter(username="owner").exists():
            User.objects.create_user(
                username="owner",
                password="password",  # Set a default password
                role="owner",  # Set the role to owner
            )


@receiver(post_migrate)
def create_default_vat_setting(sender, **kwargs):
    if (
        kwargs["app_config"].name == "accounts"
    ):  # Ensure this runs only for the accounts app
        # Check if a VAT setting already exists
        if not VATSetting.objects.exists():
            VATSetting.objects.create(vat_percentage=0)  # Default VAT tax as 0
