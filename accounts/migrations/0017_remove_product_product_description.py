# Generated by Django 5.1.2 on 2024-11-13 04:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_order_order_change_order_order_paid_amount'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='product_description',
        ),
    ]