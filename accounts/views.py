from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import CustomUser
from .serializers import UserSerializer
from rest_framework.authtoken.models import Token


@api_view(['POST'])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'success': 'User registered successfully!'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    # Authenticate user
    user = authenticate(request, username=username, password=password)

    if user is not None:
        # Generate token if the user is authenticated
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'firstName': user.first_name,
            'lastName': user.last_name
        }, status=status.HTTP_200_OK)  # Optionally send back first and last names

    return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
