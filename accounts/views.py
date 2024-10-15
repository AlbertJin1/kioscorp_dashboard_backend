from django.contrib.auth import authenticate, logout as django_logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import CustomUser, Log, MainCategory, SubCategory, Product
from .serializers import (
    UserSerializer,
    LogSerializer,
    MainCategorySerializer,
    SubCategorySerializer,
    ProductSerializer,
    ProductWithSubCategorySerializer,
)
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import IsOwnerOrAdmin
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
import socket
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os


# FOR PRINTING IN KIOSK
RPI_IP = "192.168.254.183"
RPI_PORT = 8001  # Use port 8001 to connect to the print server


@api_view(["POST"])
def print_receipt(request):
    try:
        print_data = request.data

        # Create a socket connection to the Raspberry Pi
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((RPI_IP, RPI_PORT))
            s.sendall(json.dumps(print_data).encode("utf-8"))
            response = s.recv(1024).decode("utf-8")

        if "completed successfully" in response:
            return JsonResponse(
                {"success": True, "message": "Print job sent successfully"}
            )
        else:
            return JsonResponse(
                {"success": False, "message": response},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    except Exception as e:
        print(f"Error in print_receipt: {str(e)}")
        return JsonResponse(
            {"success": False, "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def validate_session(request):
    user = request.user
    if user.is_authenticated:
        # Return relevant user details
        return Response(
            {
                "firstName": user.first_name,
                "lastName": user.last_name,
                "email": user.email,
                "phoneNumber": user.phone_number,
                "role": user.role,
            },
            status=status.HTTP_200_OK,
        )
    else:
        return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)


class LogView(APIView):
    def get(self, request):
        logs = Log.objects.all().order_by("-timestamp")
        serializer = LogSerializer(logs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LogSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data["username"]
            action = serializer.validated_data["action"]
            timestamp = serializer.validated_data["timestamp"].replace(microsecond=0)

            # Use .get_or_create for logging
            log, created = Log.objects.get_or_create(
                username=username, action=action, timestamp=timestamp
            )
            if created:
                return Response(serializer.data, status=201)
            else:
                return Response({"message": "Log entry already exists"}, status=409)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        Log.objects.all().delete()
        Log.objects.create(username=request.user.username, action="Deleted all logs")
        return Response(status=204)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    request.data["role"] = "employee"  # Set role to Employee by default

    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        Log.objects.create(username=serializer.data["username"], action="Registered")
        return Response(
            {"success": "User registered successfully!"}, status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def register_owner(request):
    if request.data.get("secretPasskey") != "Practice?Noon?Along?Direct0?Must":
        return Response(
            {"error": "Invalid secret passkey."}, status=status.HTTP_400_BAD_REQUEST
        )

    request.data["role"] = "owner"  # Set role to Owner

    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        Log.objects.create(
            username=serializer.data["username"], action="Registered as owner"
        )
        return Response(
            {"success": "Owner registered successfully!"},
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])  # Ensure login doesn't require authentication
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(request, username=username, password=password)

    if user is not None:
        token, created = Token.objects.get_or_create(user=user)
        Log.objects.create(username=username, action="Logged in")
        return Response(
            {
                "token": token.key,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "email": user.email,
                "phoneNumber": user.phone_number,
                "gender": user.gender,
                "role": user.role,
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    # Log the logout action
    Log.objects.create(username=request.user.username, action="Logged out")

    # Delete the token to log out the user
    request.user.auth_token.delete()
    return Response({"success": "Logged out successfully!"}, status=status.HTTP_200_OK)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user  # The authenticated user making the request
    data = request.data

    user.first_name = data.get("firstName", user.first_name)
    user.last_name = data.get("lastName", user.last_name)
    user.phone_number = data.get("phoneNumber", user.phone_number)
    user.gender = data.get("gender", user.gender)  # Update gender if provided

    user.save()  # Save changes to the user instance
    Log.objects.create(username=user.username, action="Updated profile")
    return Response(
        {
            "success": "Profile updated successfully!",
            "role": user.role,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_profile_picture(request):
    user = request.user  # The authenticated user making the request
    if "profilePicture" in request.FILES:
        if user.profile_picture:
            user.profile_picture.delete()
        user.profile_picture = request.FILES["profilePicture"]
        user.save()  # Save changes to the user instance
        Log.objects.create(username=user.username, action="Updated profile picture")
        return Response(
            {
                "success": "Profile picture updated successfully!",
            },
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {
                "error": "No profile picture provided.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_profile_picture(request):
    user = request.user  # The authenticated user making the request
    if user.profile_picture:
        return HttpResponse(user.profile_picture, content_type="image/jpeg")
    else:
        return Response(
            {
                "error": "No profile picture available.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["GET"])
@permission_classes(
    [IsAuthenticated, IsOwnerOrAdmin]
)  # Only admins or owners can access
def get_profile_picture_admin(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        if user.profile_picture:
            return HttpResponse(user.profile_picture, content_type="image/jpeg")
        else:
            return Response(
                {"error": "No profile picture available."},
                status=status.HTTP_404_NOT_FOUND,
            )
    except CustomUser.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    current_password = request.data.get("current_password")
    new_password = request.data.get("new_password")

    # Check if the current password is valid
    if not user.check_password(current_password):
        return Response(
            {"error": "Current password is incorrect"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate the new password
    if len(new_password) < 8:
        return Response(
            {"error": "New password must be at least 8 characters long"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Set the new password
    user.set_password(new_password)
    user.save()

    # Log the password change
    Log.objects.create(username=user.username, action="Changed password")
    return Response(
        {"success": "Password changed successfully!"}, status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def get_users(request):
    users = CustomUser.objects.all()
    serializer = UserSerializer(users, many=True)

    # Create a log entry only if one doesn't already exist for the same action and timestamp
    timestamp = timezone.now()
    existing_log = Log.objects.filter(
        username=request.user.username,
        action="Viewed all users",
        timestamp__gte=timestamp - timedelta(seconds=1),
    ).exists()

    if not existing_log:
        Log.objects.create(
            username=request.user.username,
            action="Viewed all users",
            timestamp=timestamp,
        )

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_user(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        Log.objects.create(
            username=serializer.data["username"], action="Added new user"
        )
        return Response(
            {"success": "User added successfully!"}, status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def get_user_by_id(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        serializer = UserSerializer(user)
        Log.objects.create(
            username=request.user.username, action=f"Viewed user {user.username}"
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
    except CustomUser.DoesNotExist:
        return Response({"error": "User not found!"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["PUT"])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def update_user(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            Log.objects.create(
                username=request.user.username, action=f"Updated user {user.username}"
            )
            return Response(
                {"success": "User updated successfully!"}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except CustomUser.DoesNotExist:
        return Response({"error": "User not found!"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_user(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)

        # Check if the request user is trying to delete their own account
        if request.user == user:
            return Response(
                {"error": "You cannot delete your own account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check if the user is an admin
        if request.user.role == "admin":
            return Response(
                {"error": "Admins cannot delete users."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # If it's an owner, they can delete other users
        username = user.username  # Store the username for logging
        user.delete()  # Delete the user
        Log.objects.create(
            username=request.user.username,
            action=f"Deleted user {
                           username}",
        )  # Log the deletion

        return Response(
            {"success": "User deleted successfully!"}, status=status.HTTP_204_NO_CONTENT
        )
    except CustomUser.DoesNotExist:
        return Response({"error": "User not found!"}, status=status.HTTP_404_NOT_FOUND)


class MainCategoryView(APIView):
    def get(self, request):
        main_categories = MainCategory.objects.all()
        serializer = MainCategorySerializer(main_categories, many=True)
        Log.objects.create(
            username=request.user.username, action="Viewed all main categories"
        )
        return Response(serializer.data)

    def post(self, request):
        serializer = MainCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            Log.objects.create(
                username=request.user.username, action="Added a new main category"
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubCategoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sub_categories = SubCategory.objects.all()
        serializer = SubCategorySerializer(sub_categories, many=True)
        Log.objects.create(
            username=request.user.username, action="Viewed all sub categories"
        )
        return Response(serializer.data)

    def post(self, request):
        serializer = SubCategorySerializer(data=request.data)
        if serializer.is_valid():
            sub_category = serializer.save()
            Log.objects.create(
                username=request.user.username,
                action=f"Added a new sub category: {sub_category.sub_category_name} in {sub_category.main_category.main_category_name}",
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, sub_category_id):
        try:
            sub_category = SubCategory.objects.get(sub_category_id=sub_category_id)
            serializer = SubCategorySerializer(
                sub_category,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            if serializer.is_valid():
                serializer.save()
                Log.objects.create(
                    username=request.user.username,
                    action=f"Updated subcategory {sub_category.sub_category_name}",
                )
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except SubCategory.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, sub_category_id):
        try:
            sub_category = SubCategory.objects.get(sub_category_id=sub_category_id)
            if Product.objects.filter(sub_category=sub_category).exists():
                return Response(
                    {"error": "Cannot delete subcategory. It has associated products."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            sub_category.delete()
            Log.objects.create(
                username=request.user.username,
                action=f"Deleted subcategory {sub_category.sub_category_name}",
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except SubCategory.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class CreateSubCategoryView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def post(self, request):
        serializer = SubCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            Log.objects.create(
                username=request.user.username, action="Added a new sub category"
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubCategoryCountView(APIView):
    def get(self, request, main_category):
        count = SubCategory.objects.filter(main_category=main_category).count()
        return Response({"count": count})


class ProductView(APIView):
    def get(self, request):
        category = request.GET.get("category")  # Accept a category query parameter
        subcategory = request.GET.get(
            "subcategory"
        )  # Accept a subcategory query parameter
        include_subcategory = (
            request.GET.get("include_subcategory", "false").lower() == "true"
        )  # Check if subcategory should be included

        # Start with the base queryset
        products = Product.objects.all()

        # Filter by category if provided
        if category:
            products = products.filter(
                sub_category__main_category__main_category_name=category
            )

        # Filter by subcategory if provided
        if subcategory:
            products = products.filter(sub_category__sub_category_name=subcategory)

        # Choose the serializer based on the include_subcategory flag
        if include_subcategory:
            serializer = ProductWithSubCategorySerializer(
                products, many=True
            )  # Use this serializer if subcategory is needed
        else:
            serializer = ProductSerializer(
                products, many=True
            )  # Use original serializer if not needed

        Log.objects.create(username=request.user.username, action="Viewed all products")
        return Response(serializer.data)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            Log.objects.create(
                username=request.user.username, action="Added a new product"
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetailView(APIView):
    def get(self, request, product_id):
        try:
            product = Product.objects.get(product_id=product_id)
            serializer = ProductSerializer(product)
            Log.objects.create(
                username=request.user.username,
                action=f"Viewed product {product.product_name}",
            )
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, product_id):
        try:
            product = Product.objects.get(product_id=product_id)
            serializer = ProductSerializer(product, data=request.data)
            if serializer.is_valid():
                serializer.save()
                Log.objects.create(
                    username=request.user.username,
                    action=f"Updated product {product.product_name}",
                )
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, product_id):
        try:
            product = Product.objects.get(product_id=product_id)
            serializer = ProductSerializer(
                product, data=request.data, partial=True
            )  # `partial=True` allows partial updates
            if serializer.is_valid():
                serializer.save()
                Log.objects.create(
                    username=request.user.username,
                    action=f"Partially updated product {product.product_name}",
                )
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, product_id):
        try:
            product = Product.objects.get(product_id=product_id)
            # Delete the associated product image
            if product.product_image:
                product.product_image.delete()
            product.delete()
            Log.objects.create(
                username=request.user.username,
                action=f"Deleted product {product.product_name}",
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Product.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
