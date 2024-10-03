from django.contrib.auth import authenticate, logout as django_logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import CustomUser, Log
from .serializers import UserSerializer, LogSerializer
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from .permissions import IsOwnerOrAdmin
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta


class LogView(APIView):
    def get(self, request):
        logs = Log.objects.all().order_by('-timestamp')
        serializer = LogSerializer(logs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LogSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            action = serializer.validated_data['action']
            timestamp = serializer.validated_data['timestamp'].replace(
                microsecond=0)

            # Use .get_or_create for logging
            log, created = Log.objects.get_or_create(
                username=username,
                action=action,
                timestamp=timestamp
            )
            if created:
                return Response(serializer.data, status=201)
            else:
                return Response({'message': 'Log entry already exists'}, status=409)

    def delete(self, request):
        Log.objects.all().delete()
        return Response(status=204)

    def delete(self, request):
        Log.objects.all().delete()
        return Response(status=204)


@api_view(['POST'])
def register(request):
    request.data['role'] = 'employee'  # Set role to Employee by default

    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        Log.objects.create(
            username=serializer.data['username'], action='Registered')
        return Response({'success': 'User registered successfully!'}, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def register_owner(request):
    if request.data.get('secretPasskey') != "Practice?Noon?Along?Direct0?Must":
        return Response({'error': 'Invalid secret passkey.'}, status=status.HTTP_400_BAD_REQUEST)

    request.data['role'] = 'owner'  # Set role to Owner

    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        Log.objects.create(
            username=serializer.data['username'], action='Registered as owner')
        return Response({'success': 'Owner registered successfully!'}, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(request, username=username, password=password)

    if user is not None:
        token, created = Token.objects.get_or_create(user=user)
        Log.objects.create(username=username, action='Logged in')
        return Response({
            'token': token.key,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'email': user.email,
            'phoneNumber': user.phone_number,
            'gender': user.gender,
            'role': user.role,
        }, status=status.HTTP_200_OK)

    return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    # Log the logout action
    Log.objects.create(username=request.user.username, action='Logged out')

    # Delete the token to log out the user
    request.user.auth_token.delete()
    return Response({'success': 'Logged out successfully!'}, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user  # The authenticated user making the request
    data = request.data

    user.first_name = data.get('firstName', user.first_name)
    user.last_name = data.get('lastName', user.last_name)
    user.phone_number = data.get('phoneNumber', user.phone_number)
    user.gender = data.get('gender', user.gender)  # Update gender if provided

    user.save()  # Save changes to the user instance
    Log.objects.create(username=user.username, action='Updated profile')
    return Response({
        'success': 'Profile updated successfully!',
        'role': user.role,
    }, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')

    # Check if the current password is valid
    if not user.check_password(current_password):
        return Response({'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate the new password (You can customize this validation logic as needed)
    if len(new_password) < 8:
        return Response({'error': 'New password must be at least 8 characters long'}, status=status.HTTP_400_BAD_REQUEST)

    # Set the new password
    user.set_password(new_password)
    user.save()

    # Log the password change
    Log.objects.create(username=user.username, action='Changed password')
    return Response({'success': 'Password changed successfully!'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def get_users(request):
    users = CustomUser.objects.all()
    serializer = UserSerializer(users, many=True)

    # Create a log entry only if one doesn't already exist for the same action and timestamp
    timestamp = timezone.now()
    existing_log = Log.objects.filter(
        username=request.user.username, action='Viewed all users', timestamp__gte=timestamp - timedelta(seconds=1)).exists()

    if not existing_log:
        Log.objects.create(username=request.user.username,
                           action='Viewed all users', timestamp=timestamp)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_user(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        Log.objects.create(
            username=serializer.data['username'], action='Added new user')
        return Response({'success': 'User added successfully!'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def get_user_by_id(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        serializer = UserSerializer(user)
        Log.objects.create(username=request.user.username,
                           action=f'Viewed user {user.username}')
        return Response(serializer.data, status=status.HTTP_200_OK)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found!'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def update_user(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            Log.objects.create(username=request.user.username,
                               action=f'Updated user {user.username}')
            return Response({'success': 'User updated successfully!'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found!'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)

        # Check if the request user is trying to delete their own account
        if request.user == user:
            return Response({'error': 'You cannot delete your own account.'}, status=status.HTTP_403_FORBIDDEN)

        # Check if the user is an admin
        if request.user.role == 'admin':
            return Response({'error': 'Admins cannot delete users.'}, status=status.HTTP_403_FORBIDDEN)

        # If it's an owner, they can delete other users
        username = user.username  # Store the username for logging
        user.delete()  # Delete the user
        Log.objects.create(username=request.user.username, action=f'Deleted user {
                           username}')  # Log the deletion

        return Response({'success': 'User deleted successfully!'}, status=status.HTTP_204_NO_CONTENT)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found!'}, status=status.HTTP_404_NOT_FOUND)
