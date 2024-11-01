# Generated by Django 5.1 on 2024-10-25 04:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_customer_nextcustomerid_nextorderid_nextorderitemid_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('feedback_id', models.AutoField(primary_key=True, serialize=False)),
                ('feedback_rating', models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])),
                ('feedback_satisfaction', models.CharField(choices=[('Not Satisfied', 'Not Satisfied'), ('Slightly Satisfied', 'Slightly Satisfied'), ('Neutral', 'Neutral'), ('Satisfied', 'Satisfied'), ('Very Satisfied', 'Very Satisfied')], max_length=50)),
                ('feedback_date', models.DateTimeField(auto_now_add=True)),
                ('customer_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.customer')),
                ('order_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.order')),
            ],
        ),
    ]