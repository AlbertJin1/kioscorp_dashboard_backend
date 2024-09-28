from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    # You can add additional fields if necessary
    first_name = models.CharField(max_length=30, blank=False)
    last_name = models.CharField(max_length=30, blank=False)
    gender = models.CharField(max_length=10, blank=False)
    phone_number = models.CharField(max_length=15, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
