# serializers.py
from rest_framework import serializers
from .models import (
    CustomUser,
    Log,
    MainCategory,
    SubCategory,
    Product,
    Feedback,
    Order,
    OrderItem,
)


class UserSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)  # Add id field
    firstName = serializers.CharField(source="first_name", required=True)
    lastName = serializers.CharField(source="last_name", required=True)
    email = serializers.EmailField(required=True)
    phoneNumber = serializers.CharField(source="phone_number", required=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "firstName",
            "lastName",
            "email",
            "gender",
            "phoneNumber",
            "password",
            "role",
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        # Set the role to employee by default if not provided (for regular registration)
        role = validated_data.get("role", "employee")

        user = CustomUser(
            username=validated_data["username"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
            gender=validated_data["gender"],
            phone_number=validated_data["phone_number"],
            role=role,  # Role is passed or defaults to employee
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class UpdateProfileSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "gender",
            "profile_picture",
        ]


class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ["id", "username", "action", "timestamp"]


class MainCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MainCategory
        fields = ["main_category_id", "main_category_name"]


# serializers.py
class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = [
            "sub_category_id",
            "sub_category_name",
            "main_category",
            "sub_category_image",
        ]

    def update(self, instance, validated_data):
        instance.sub_category_name = validated_data.get(
            "sub_category_name", instance.sub_category_name
        )
        instance.sub_category_image = validated_data.get(
            "sub_category_image", instance.sub_category_image
        )
        instance.save()
        Log.objects.create(
            username=self.context["request"].user.username,
            action=f"Updated subcategory {instance.sub_category_name}",
        )
        return instance


# serializers.py
class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = [
            "product_id",
            "product_image",
            "product_name",
            "product_type",
            "product_size",
            "product_brand",
            "product_color",
            "product_quantity",
            "product_description",
            "product_price",
            "product_added",
            "sub_category",
            "product_sold",
        ]


class ProductWithSubCategorySerializer(serializers.ModelSerializer):
    sub_category = SubCategorySerializer()  # Include subcategory details

    class Meta:
        model = Product
        fields = [
            "product_id",
            "product_image",
            "product_name",
            "product_type",
            "product_size",
            "product_brand",
            "product_color",
            "product_quantity",
            "product_description",
            "product_price",
            "product_added",
            "sub_category",  # Ensure this is included
            "product_sold",
        ]


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = [
            "feedback_id",
            "order_id",
            "feedback_rating",
            "feedback_satisfaction",
            "feedback_date",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    product_image = serializers.ImageField(
        source="product.product_image", read_only=True
    )  # Include product image

    class Meta:
        model = OrderItem
        fields = [
            "order_item_id",
            "product",
            "product_price",
            "order_item_quantity",
            "product_name",
            "product_image",  # Add product_image to fields
        ]


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(
        many=True, source="orderitem_set"
    )  # Include order items

    class Meta:
        model = Order
        fields = [
            "order_id",
            "order_amount",
            "order_paid_amount",  # Include the new fields
            "order_change",
            "order_date_created",
            "order_status",
            "order_items",
        ]


class SalesDataSerializer(serializers.Serializer):
    daily_sales = serializers.DecimalField(max_digits=10, decimal_places=2)
    annual_sales = serializers.DecimalField(max_digits=10, decimal_places=2)


class OrderItemHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.product_name")
    product_size = serializers.CharField(source="product.product_size")  # Add this line
    product_image = serializers.SerializerMethodField()
    unit_price = serializers.FloatField(
        source="product_price"
    )  # Ensure unit_price is a float
    quantity = serializers.IntegerField(source="order_item_quantity")
    date_created = serializers.DateTimeField(source="order.order_date_created")
    status = serializers.CharField(source="order.order_status")

    class Meta:
        model = OrderItem
        fields = [
            "product_name",
            "product_size",  # Include product_size in fields
            "product_image",
            "unit_price",
            "quantity",
            "date_created",
            "status",
        ]

    def get_product_image(self, obj):
        return obj.product.product_image.url if obj.product.product_image else None
