from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('employee', 'Employee'),
    )

    # Additional fields
    gender = models.CharField(max_length=10, choices=[(
        'Male', 'Male'), ('Female', 'Female')], blank=False)
    phone_number = models.CharField(max_length=15, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    role = models.CharField(
        max_length=10, choices=ROLE_CHOICES, default='employee')

    def __str__(self):
        return self.username


class Log(models.Model):
    username = models.CharField(max_length=255)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
