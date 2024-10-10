from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser (AbstractUser):
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
    profile_picture = models.ImageField(upload_to='user_profile/', blank=True, null=True)

    def __str__(self):
        return self.username


class Log(models.Model):
    username = models.CharField(max_length=255)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)


class MainCategory(models.Model):
    main_category_id = models.AutoField(primary_key=True)
    main_category_name = models.CharField(max_length=255)

    def __str__(self):
        return self.main_category_name


class NextSubCategoryId(models.Model):
    next_id = models.IntegerField(default=1)

class NextProductId(models.Model):
    next_id = models.IntegerField(default=1)

class SubCategory(models.Model):
    sub_category_id = models.AutoField(primary_key=True)
    sub_category_name = models.CharField(max_length=255)
    main_category = models.ForeignKey(MainCategory, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.sub_category_id:
            next_id = NextSubCategoryId.objects.first()
            if next_id:
                year = timezone.now().year
                month = timezone.now().month
                self.sub_category_id = f"{year}{month:02}{next_id.next_id:04}"
                next_id.next_id += 1
                next_id.save()
            else:
                year = timezone.now().year
                month = timezone.now().month
                self.sub_category_id = f"{year}{month:02}0001"
                NextSubCategoryId.objects.create(next_id=2)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.sub_category_name


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    product_image = models.ImageField(upload_to="products/")
    product_name = models.CharField(max_length=255)
    product_type = models.CharField(max_length=255)
    product_size = models.CharField(max_length=255)
    product_brand = models.CharField(max_length=255)
    product_color = models.CharField(max_length=255)
    product_quantity = models.IntegerField(default=0)
    product_description = models.TextField(blank=True, null=True)  # Add this line
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_added = models.DateTimeField(auto_now_add=True)

    sub_category = models.ForeignKey(SubCategory, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.product_id:
            next_id = NextProductId.objects.first()
            if next_id:
                year = timezone.now().year
                month = timezone.now().month
                self.product_id = f"{year}{month:02}{next_id.next_id:07}"
                next_id.next_id += 1
                next_id.save()
            else:
                year = timezone.now().year
                month = timezone.now().month
                self.product_id = f"{year}{month:02}0000001"
                NextProductId.objects.create(next_id=2)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.product_name