# Generated by Django 5.1 on 2024-10-10 09:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_nextproductid_nextsubcategoryid'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='profile_picture',
            field=models.ImageField(blank=True, null=True, upload_to='media/user_profile'),
        ),
    ]
