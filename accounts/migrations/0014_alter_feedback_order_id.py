# Generated by Django 5.1 on 2024-10-25 04:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_remove_feedback_customer_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feedback',
            name='order_id',
            field=models.ForeignKey(db_column='order_id', on_delete=django.db.models.deletion.CASCADE, to='accounts.order'),
        ),
    ]
