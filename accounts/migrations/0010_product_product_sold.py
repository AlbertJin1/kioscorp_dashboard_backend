# Generated by Django 5.1 on 2024-10-13 16:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_subcategory_sub_category_image_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='product_sold',
            field=models.IntegerField(default=0),
        ),
    ]