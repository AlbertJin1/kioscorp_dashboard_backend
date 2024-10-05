from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import MainCategory


@receiver(post_migrate)
def create_default_main_categories(sender, **kwargs):
    if kwargs['app_config'].name == 'accounts':
        main_categories = [
            {'main_category_name': 'Auto Supply'},
            {'main_category_name': 'Bolts'},
        ]

        for category in main_categories:
            MainCategory.objects.get_or_create(
                main_category_name=category['main_category_name'])
