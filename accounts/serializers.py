from rest_framework import serializers
# Adjust the import if your model is in a different file
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source='first_name', required=True)
    lastName = serializers.CharField(source='last_name', required=True)
    phoneNumber = serializers.CharField(source='phone_number', required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'firstName', 'lastName', 'gender',
                  'phoneNumber', 'created_at']  # Include fields needed
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Remove the extra fields and map the names properly
        user = CustomUser(
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            gender=validated_data['gender'],
            phone_number=validated_data['phone_number'],
        )
        # Securely hash the password
        user.set_password(validated_data['password'])
        user.save()  # Save the new user instance
        return user
