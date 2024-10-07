# serializers.py
from rest_framework import serializers
from .models import CustomUser, Log, MainCategory, SubCategory, Product


class UserSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)  # Add id field
    firstName = serializers.CharField(source='first_name', required=True)
    lastName = serializers.CharField(source='last_name', required=True)
    email = serializers.EmailField(required=True)
    phoneNumber = serializers.CharField(source='phone_number', required=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'firstName', 'lastName', 'email',
                  'gender', 'phoneNumber', 'password', 'role']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Set the role to employee by default if not provided (for regular registration)
        role = validated_data.get('role', 'employee')

        user = CustomUser(
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            gender=validated_data['gender'],
            phone_number=validated_data['phone_number'],
            role=role,  # Role is passed or defaults to employee
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ['id', 'username', 'action', 'timestamp']


class MainCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MainCategory
        fields = ['main_category_id', 'main_category_name']


# serializers.py
class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ['sub_category_id', 'sub_category_name', 'main_category']


# serializers.py
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['product_id', 'product_image', 'product_name', 'product_type', 'product_size', 'product_brand',
                  'product_color', 'product_quantity', 'product_description', 'product_price', 'product_added', 'sub_category']