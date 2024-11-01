# Generated by Django 5.1 on 2024-10-27 04:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_alter_feedback_order_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(choices=[('owner', 'Owner'), ('admin', 'Admin'), ('cashier', 'Cashier')], default='cashier', max_length=10),
        ),
    ]