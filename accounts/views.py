from datetime import timedelta, datetime
from decimal import Decimal
import json
import socket
import subprocess
import os
import win32print

from django.contrib.auth import authenticate, logout as django_logout
from django.core.files.storage import default_storage
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Count, Sum, F, Prefetch
from django.db.models.functions import TruncMonth, ExtractMonth, ExtractDay, TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from .models import (
    CustomUser,
    Log,
    MainCategory,
    SubCategory,
    Product,
    Order,
    OrderItem,
    Customer,
    Feedback,
    VATSetting,
)
from .serializers import (
    UserSerializer,
    LogSerializer,
    MainCategorySerializer,
    SubCategorySerializer,
    ProductSerializer,
    ProductWithSubCategorySerializer,
    FeedbackSerializer,
    OrderSerializer,
    SalesDataSerializer,
    OrderItemHistorySerializer,
    VATSettingSerializer,
)
from .permissions import IsOwnerOrAdmin


RPI_IP = "192.168.254.183"
RPI_PORT = 8001  # Use port 8001 to connect to the print server


@api_view(["POST"])
def print_receipt(request):
    try:
        print_data = request.data

        # Start a transaction
        with transaction.atomic():
            # Create a new Customer instance (you may want to customize this)
            customer = Customer.objects.create()

            # Get the current count of pending orders (This will give us the queue number)
            pending_count = Order.objects.filter(order_status="Pending").count()

            # If no pending orders, set queue number to 1
            queue_number = 1 if pending_count == 0 else pending_count + 1

            # Create a new Order instance
            order = Order.objects.create(
                customer=customer,
                order_amount=print_data["total"],
                order_status="Pending",
            )

            # Create a new OrderItem instance for each product in the cart
            for item in print_data["items"]:
                try:
                    product = Product.objects.get(
                        product_id=item["product"]["product_id"]
                    )
                    # Create OrderItem instance
                    order_item = OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_price=item["product"]["product_price"],
                        order_item_quantity=item["quantity"],
                    )
                    # Ensure to pass color and size along with the item details
                    item["product"]["product_color"] = product.product_color
                    item["product"]["product_size"] = product.product_size

                except Product.DoesNotExist:
                    return Response(
                        {
                            "success": False,
                            "message": f"Error: Product with ID {item['product']['product_id']} does not exist.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Prepare the print data
            print_data["order_id"] = order.order_id  # Add order_id to print_data
            print_data["order_status"] = (
                order.order_status
            )  # Add order_status to print_data
            print_data["queue_number"] = queue_number  # Add queue_number to print_data

            # Pass the item details as well
            print_data["items"] = [
                {
                    "product": {
                        "product_id": item["product"]["product_id"],
                        "product_name": item["product"]["product_name"],
                        "product_price": item["product"]["product_price"],
                        "product_color": item["product"].get("product_color", "N/A"),
                        "product_size": item["product"].get("product_size", "N/A"),
                    },
                    "quantity": item["quantity"],
                }
                for item in print_data["items"]
            ]

            # Attempt to connect to the printer with a timeout
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(10)  # Set a timeout of 10 seconds
                    s.connect((RPI_IP, RPI_PORT))
                    s.sendall(json.dumps(print_data).encode("utf-8"))
                    response = s.recv(1024).decode("utf-8")

                if "completed successfully" in response:
                    # Return the order_id along with success message
                    return Response(
                        {
                            "success": True,
                            "message": "Print job sent successfully",
                            "order_id": order.order_id,  # Include the order_id in the response
                        }
                    )
                else:
                    # If printing fails, raise an exception to trigger rollback
                    raise Exception("Printing failed: " + response)

            except socket.timeout:
                # If the printer is not detected within 15 seconds, proceed to save the order
                return Response(
                    {
                        "success": True,
                        "message": "Printer not detected within 15 seconds. Order saved without printing.",
                        "order_id": order.order_id,  # Include the order_id in the response
                    }
                )

    except Exception as e:
        print(f"Error in print_receipt: {str(e)}")
        return Response(
            {"success": False, "message ": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def create_order(request):
    try:
        order_data = request.data

        # Create a new Customer instance (you may want to customize this)
        customer = Customer.objects.create()

        # Create a new Order instance
        order = Order.objects.create(
            customer=customer,
            order_amount=order_data["total"],
            order_status="Pending",
        )

        # Create a new OrderItem instance for each product in the cart
        for item in order_data["items"]:
            try:
                product = Product.objects.get(product_id=item["product"]["product_id"])

                # Check if there is enough stock for the requested quantity
                if product.product_quantity < item["quantity"]:
                    return Response(
                        {
                            "success": False,
                            "message": f"Error: Insufficient stock for {product.product_name}. Available: {product.product_quantity}, Required: {item['quantity']}.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Create the OrderItem instance if stock is sufficient
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_price=item["product"]["product_price"],
                    order_item_quantity=item["quantity"],
                )

            except Product.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "message": f"Error: Product with ID {item['product']['product_id']} does not exist.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        Log.objects.create(
            username=request.user.username,
            action=f"Created a new order with ID {order.order_id}",
        )
        return Response(
            {
                "success": True,
                "message": "Order created successfully.",
                "order_id": order.order_id,  # Include the order_id in the response
            },
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response(
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
    request.data["role"] = "cashier"  # Set role to Employee by default

    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        Log.objects.create(username=serializer.data["username"], action="Registered")
        return Response(
            {"success": "User  registered successfully!"},
            status=status.HTTP_201_CREATED,
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
        user = serializer.save()
        user.save()  # Save the user instance
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
        return Response({"error": "User  not found."}, status=status.HTTP_404_NOT_FOUND)


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
            {"success": "User  added successfully!"}, status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def get_user_by_id(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except CustomUser.DoesNotExist:
        return Response({"error": "User  not found!"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["PUT"])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def update_user(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        serializer = UserSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()  # Save the user instance
            Log.objects.create(
                username=request.user.username, action=f"Updated user {user.username}"
            )
            return Response(
                {"success": "User  updated successfully!"}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except CustomUser.DoesNotExist:
        return Response({"error": "User  not found!"}, status=status.HTTP_404_NOT_FOUND)


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
            action=f"Deleted user {username}",
        )  # Log the deletion

        return Response(
            {"success": "User  deleted successfully!"},
            status=status.HTTP_204_NO_CONTENT,
        )
    except CustomUser.DoesNotExist:
        return Response({"error": "User  not found!"}, status=status.HTTP_404_NOT_FOUND)


class MainCategoryView(APIView):
    def get(self, request):
        main_categories = MainCategory.objects.all()
        serializer = MainCategorySerializer(main_categories, many=True)
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
        return Response(serializer.data)

    def post(self, request):
        # Check for duplicate subcategory name in the same main category
        sub_category_name = request.data.get("sub_category_name")
        main_category_id = request.data.get("main_category")

        if SubCategory.objects.filter(
            sub_category_name=sub_category_name, main_category_id=main_category_id
        ).exists():
            return Response(
                {
                    "error": "A subcategory with this name already exists in the selected main category."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

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
            # Check if the subcategory has associated products
            associated_products = Product.objects.filter(sub_category=sub_category)

            if associated_products.exists():
                return Response(
                    {"error": "Cannot delete subcategory. It has associated products."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Proceed with deletion if no associated products
            if sub_category.sub_category_image:
                default_storage.delete(sub_category.sub_category_image.path)

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
        # Check for duplicate subcategory name in the same main category
        sub_category_name = request.data.get("sub_category_name")
        main_category_id = request.data.get("main_category")

        if SubCategory.objects.filter(
            sub_category_name=sub_category_name, main_category_id=main_category_id
        ).exists():
            return Response(
                {
                    "error": "A subcategory with this name already exists in the selected main category."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

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


class FeedbackCreateView(APIView):
    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])  # Allow any user to access this endpoint
def reset_password(request):
    username = request.data.get("username")
    new_password = request.data.get("newPassword")

    try:
        user = CustomUser.objects.get(username=username)
        user.set_password(new_password)
        user.save()
        Log.objects.create(
            username=username, action=f"Reset password for {username}"
        )  # Log the action for the user being reset
        return Response(
            {"success": f"Password for {username} has been reset."},
            status=status.HTTP_200_OK,
        )
    except CustomUser.DoesNotExist:
        return Response({"error": "User  not found."}, status=status.HTTP_404_NOT_FOUND)


class PendingOrdersView(APIView):
    def get(self, request):
        pending_orders = Order.objects.filter(order_status="Pending")
        serializer = OrderSerializer(pending_orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VoidOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):
        try:
            # Ensure the user is authenticated
            if not request.user.is_authenticated:
                return Response(
                    {"error": "User is not authenticated."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Fetch the order by ID
            order = Order.objects.get(order_id=order_id)
            order.order_status = "Void"  # Update the order status to "Void"
            order.order_cashier = f"{request.user.first_name} {request.user.last_name}"
            order.save()  # Save the changes

            # Log the void action
            Log.objects.create(
                username=request.user.username, action=f"Voided order {order_id}"
            )

            return Response(
                {"message": "Order successfully voided."}, status=status.HTTP_200_OK
            )

        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND
            )


def is_printer_ready(printer_name):
    try:
        hprinter = win32print.OpenPrinter(printer_name)
        printer_info = win32print.GetPrinter(hprinter, 2)
        win32print.ClosePrinter(hprinter)

        # Check if the printer is ready
        status = printer_info["Status"]
        print(f"Printer status code: {status}")

        # Check for printer statuses
        if status == 0:  # 0 indicates the printer is ready
            return True
        elif (
            status & win32print.PRINTER_STATUS_OFFLINE
        ):  # Check if the printer is offline
            print("Printer is offline.")
            return False
        elif status in (
            1,
            2,
            3,
            4,
            5,
        ):  # 1: paused, 2: error, 3: pending deletion, 4: paper jam, 5: other errors
            print("Printer is not ready or has an issue.")
            return False
        else:
            print("Printer is in an unknown state.")
            return False
    except Exception as e:
        print(f"Error checking printer status: {str(e)}")
        return False


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def pay_order(request, order_id):
    try:
        # Check if the printer is ready before processing the payment
        printer_name = "POS58 v9"  # Replace with your actual printer name
        if not is_printer_ready(printer_name):
            return Response(
                {"error": "Printer is not ready. Please check the printer connection."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        with transaction.atomic():
            order = Order.objects.get(order_id=order_id)

            # Check stock availability before processing the payment
            for item in order.orderitem_set.all():
                product = item.product
                if product.product_quantity < item.order_item_quantity:
                    return Response(
                        {
                            "error": f"Insufficient stock for {product.product_name}. Available: {product.product_quantity}, Required: {item.order_item_quantity}.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            amount_given = request.data.get("order_paid_amount")
            amount_given = Decimal(amount_given)

            # Calculate subtotal using discounted prices
            subtotal = sum(
                (item.discounted_price or item.product_price) * item.order_item_quantity
                for item in order.orderitem_set.all()
            )

            # Get the VAT percentage from the request data
            vat_percentage = request.data.get(
                "vat_percentage", 0
            )  # Default to 0 if not provided
            vat_percentage = float(
                vat_percentage
            )  # Ensure it's a float for calculations

            # Convert vat_percentage to Decimal
            vat_percentage = Decimal(vat_percentage)

            vat_amount = subtotal * (vat_percentage / 100)  # Calculate VAT amount
            total_amount = subtotal + vat_amount  # Total including VAT
            change = amount_given - total_amount

            if change < 0:
                return Response(
                    {"error": "Insufficient amount provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update the order details
            order.order_status = "Paid"
            order.order_paid_amount = amount_given
            order.order_change = change
            order.order_amount = total_amount  # Update to total amount after VAT
            order.order_cashier = f"{request.user.first_name} {request.user.last_name}"
            order.save()

            # Update product quantities and sold counts
            for item in order.orderitem_set.all():
                product = item.product
                product.product_quantity -= item.order_item_quantity
                product.product_sold += item.order_item_quantity
                product.save()

            # Get the cashier's name from the request data
            cashier_first_name = request.data.get("cashier_first_name", "Puerto")
            cashier_last_name = request.data.get("cashier_last_name", "")
            cashier_name = f"{cashier_first_name} {cashier_last_name}".strip()

            # Prepare data for printing
            print_data = {
                "items": [
                    {
                        "product": {
                            "product_id": item.product.product_id,
                            "product_name": item.product.product_name,
                            "product_price": float(item.product.product_price),
                        },
                        "quantity": item.order_item_quantity,
                        "color": item.product.product_color,
                        "size": item.product.product_size,
                    }
                    for item in order.orderitem_set.all()
                ],
                "subtotal": float(subtotal),  # Include subtotal
                "total": float(total_amount),  # Total after VAT
                "order_id": order.order_id,
                "order_status": order.order_status,
                "paid_amount": float(amount_given),
                "change": float(change),
                "cashier": cashier_name,
                "vat_percentage": vat_percentage,  # Include VAT percentage
                "fallback_time": datetime.now().isoformat(),
            }

            # Send print data to the print receipt function
            print_receiptPOS(print_data)

            Log.objects.create(
                username=request.user.username, action=f"Paid for order {order_id}"
            )
            return Response(
                {"success": "Order successfully paid.", "order_id": order.order_id},
                status=status.HTTP_200_OK,
            )

    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def convert_decimals_to_floats(data):
    if isinstance(data, dict):
        return {key: convert_decimals_to_floats(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_decimals_to_floats(item) for item in data]
    elif isinstance(data, Decimal):
        return float(data)  # Convert Decimal to float
    return data


def print_receiptPOS(print_data):
    try:
        # Convert Decimal values to float
        print_data = convert_decimals_to_floats(print_data)

        # Convert print_data to JSON string for passing to the print script
        print_data_json = json.dumps(print_data)

        # Define the relative path to the print_receiptPOS.py script
        script_path = os.path.join(os.path.dirname(__file__), "print_receiptPOS.py")

        # Call the print script with the print data as an argument
        process = subprocess.Popen(
            ["python", script_path, print_data_json],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for the process to complete and get the output
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            return True  # Printing was successful
        else:
            raise Exception(f"Printing failed: {stderr.decode('utf-8')}")

    except Exception as e:
        raise Exception(f" Error in print_receiptPOS: {str(e)}")


@api_view(["GET"])
@permission_classes([IsAuthenticated])  # Require authentication
def order_counts(request):
    total_paid_orders = Order.objects.filter(order_status="Paid").count()
    total_pending_orders = Order.objects.filter(order_status="Pending").count()
    total_void_orders = Order.objects.filter(
        order_status="Void"
    ).count()  # Add this line

    return Response(
        {
            "totalPaidOrders": total_paid_orders,
            "totalPendingOrders": total_pending_orders,
            "totalVoidOrders": total_void_orders,  # Add this line
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])  # Require authentication for this endpoint
def satisfaction_overview(request):
    # Get the selected year from the query parameters
    selected_year = request.query_params.get("year", None)

    # Filter feedback based on the selected year
    feedback_queryset = Feedback.objects.all()
    if selected_year:
        feedback_queryset = feedback_queryset.filter(feedback_date__year=selected_year)

    # Aggregate satisfaction ratings
    satisfaction_counts = feedback_queryset.values("feedback_satisfaction").annotate(
        count=Count("feedback_satisfaction")
    )

    # Prepare the response data
    satisfaction_data = {
        satisfaction["feedback_satisfaction"]: satisfaction["count"]
        for satisfaction in satisfaction_counts
    }

    return Response(satisfaction_data)


class CustomerCountByMonthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, view_type):
        current_year = timezone.now().year
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if view_type == "month":
            # Get the selected year from query params, default to current year
            selected_year = int(request.query_params.get("year", current_year))
            order_counts = (
                Order.objects.filter(
                    order_status="Paid", order_date_created__year=selected_year
                )
                .annotate(month=ExtractMonth("order_date_created"))
                .values("month")
                .annotate(count=Count("order_id"))
                .order_by("month")
            )
            # Initialize data with 0s for each month
            data = [0] * 12
            for entry in order_counts:
                data[entry["month"] - 1] = entry["count"]

            return Response(data)

        elif view_type == "day":
            # Get year and month from query parameters
            selected_year = int(request.query_params.get("year", current_year))
            selected_month = int(
                request.query_params.get("month", timezone.now().month)
            )

            if start_date and end_date:
                year, month, _ = start_date.split(
                    "-"
                )  # Extract year and month from start_date
                order_counts = (
                    Order.objects.filter(
                        order_status="Paid",
                        order_date_created__year=year,
                        order_date_created__month=month,
                    )
                    .annotate(day=ExtractDay("order_date_created"))
                    .values("day")
                    .annotate(count=Count("order_id"))
                    .order_by("day")
                )
                # Initialize data with 0s for up to 31 days
                data = [0] * 31
                for entry in order_counts:
                    data[entry["day"] - 1] = entry["count"]

                # If it's the current month, show only past and current days
                if timezone.now().month == int(month) and timezone.now().year == int(
                    year
                ):
                    today = timezone.now().day
                    data = data[
                        :today
                    ]  # Limit the data to only include days up to today

            return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def top_selling_products(request):
    # Get the selected year from the query parameters (default to current year if not provided)
    selected_year = request.query_params.get("year", timezone.now().year)
    monthly_top_products = []

    # Loop through each month (1-12)
    for month in range(1, 13):
        # Get total quantity sold for each product in this month, filter by minimum total_sold, and limit to 7 results
        monthly_sales = (
            OrderItem.objects.filter(
                order__order_date_created__year=selected_year,  # Filter by selected year
                order__order_date_created__month=month,
            )
            .values("product_id")
            .annotate(total_sold=Sum("order_item_quantity"))
            .filter(total_sold__gte=20)  # Only include products with total_sold >= 20
            .order_by("-total_sold")[:7]  # Limit to top 7 results
        )

        for product_data in monthly_sales:
            product_details = Product.objects.get(pk=product_data["product_id"])
            monthly_top_products.append(
                {
                    "product_id": product_details.product_id,
                    "product_name": product_details.product_name,
                    "product_image": request.build_absolute_uri(
                        product_details.product_image.url
                    ),
                    "product_type": product_details.product_type,  # Include product type
                    "product_color": product_details.product_color,
                    "product_size": product_details.product_size,  # Include product size
                    "top_selling_month": timezone.datetime(
                        int(selected_year), month, 1
                    ).strftime(
                        "%B"
                    ),  # Display month name
                    "total_sold": product_data["total_sold"],
                }
            )

    return Response(monthly_top_products)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def low_selling_products(request):
    current_year = timezone.now().year
    monthly_low_products = []

    # Loop through each month (1-12)
    for month in range(1, 13):
        # Get total quantity sold for each product in this month, filter by maximum total_sold, and limit to 7 results
        monthly_sales = (
            OrderItem.objects.filter(
                order__order_date_created__year=current_year,
                order__order_date_created__month=month,
            )
            .values("product_id")
            .annotate(total_sold=Sum("order_item_quantity"))
            .filter(total_sold__lt=20)  # Only include products with total_sold < 10
            .order_by("total_sold")[:7]  # Limit to bottom 7 results (lowest sold)
        )

        for product_data in monthly_sales:
            product_details = Product.objects.get(pk=product_data["product_id"])
            monthly_low_products.append(
                {
                    "product_id": product_details.product_id,
                    "product_name": product_details.product_name,
                    "product_image": request.build_absolute_uri(
                        product_details.product_image.url
                    ),
                    "product_type": product_details.product_type,  # Include product type
                    "product_color": product_details.product_color,
                    "product_size": product_details.product_size,  # Include product size
                    "low_selling_month": timezone.datetime(
                        current_year, month, 1
                    ).strftime(
                        "%B"
                    ),  # Display month name
                    "total_sold": product_data["total_sold"],
                }
            )

    return Response(monthly_low_products)


@api_view(["GET"])
def get_sales_data(request):
    today = timezone.now().date()
    current_year = timezone.now().year

    # Calculate daily sales for orders with status "Paid"
    daily_sales = (
        Order.objects.filter(
            order_date_created__date=today, order_status="Paid"
        ).aggregate(total=Sum("order_amount"))["total"]
        or 0
    )

    # Calculate annual sales for orders with status "Paid"
    annual_sales = (
        Order.objects.filter(
            order_date_created__year=current_year, order_status="Paid"
        ).aggregate(total=Sum("order_amount"))["total"]
        or 0
    )

    # Create response data
    sales_data = {
        "daily_sales": daily_sales,
        "annual_sales": annual_sales,
    }

    serializer = SalesDataSerializer(data=sales_data)
    serializer.is_valid(raise_exception=True)

    return Response(serializer.data)


def get_paid_orders_by_month():
    # Get the current month and year
    current_year = timezone.now().year
    current_month = timezone.now().month

    # Query orders with "Paid" status, grouped by month
    paid_orders = (
        Order.objects.filter(
            order_status="Paid",
            order_date_created__year=current_year,
            order_date_created__month=current_month,
        )
        .annotate(month=TruncMonth("order_date_created"))
        .values("month")
        .annotate(total_orders=Count("order_id"), total_amount=Sum("order_amount"))
        .order_by("month")
    )

    return paid_orders


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_history(request):
    status_filter = request.GET.get("status", "all")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    order_number = request.GET.get("order_number")

    # Apply filtering based on order status and order by date in descending order
    orders = Order.objects.all().order_by("-order_date_created")

    if status_filter != "all":
        status_map = {"completed": "Paid", "pending": "Pending", "cancelled": "Void"}
        orders = orders.filter(order_status=status_map.get(status_filter, ""))

    if start_date:
        orders = orders.filter(order_date_created__date__gte=parse_date(start_date))

    if end_date:
        orders = orders.filter(order_date_created__date__lte=parse_date(end_date))

    if order_number:
        orders = orders.filter(order_id__icontains=order_number)

    # Group items by order_id
    grouped_orders = []
    for order in orders:
        items = []
        for item in order.orderitem_set.all():
            # Check if the product exists
            if item.product is not None:  # This checks if the product is not deleted
                product_image_url = (
                    request.build_absolute_uri(item.product.product_image.url)
                    if item.product.product_image
                    else None
                )
                items.append(
                    {
                        "product_image": product_image_url,
                        "product_name": item.product.product_name,
                        "product_color": item.product.product_color,
                        "product_size": item.product.product_size,  # Include product_size here
                        "date_created": order.order_date_created,
                        "status": order.order_status,
                        "unit_price": {
                            "original": item.product_price,
                            "discounted": item.discounted_price,
                        },
                        "quantity": item.order_item_quantity,
                    }
                )

        # Only add the order if it has items
        if items:
            grouped_orders.append(
                {
                    "order_id": order.order_id,
                    "order_cashier": order.order_cashier,  # Include order_cashier
                    "items": items,
                }
            )

    return Response(grouped_orders, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def monthly_sales(request):
    year = request.GET.get("year", timezone.now().year)
    month_start = request.GET.get("month_start", 1)
    month_end = request.GET.get("month_end", 12)

    monthly_sales_data = (
        Order.objects.filter(order_status="Paid", order_date_created__year=year)
        .annotate(month=ExtractMonth("order_date_created"))
        .values("month")
        .annotate(total_sales=Sum("order_amount"))
        .filter(month__gte=month_start, month__lte=month_end)
        .order_by("month")
    )

    # Prepare data for response
    sales_data = {month: 0 for month in range(1, 13)}  # Initialize all months to 0
    for entry in monthly_sales_data:
        sales_data[entry["month"]] = entry["total_sales"]

    return Response(sales_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def daily_sales(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if not start_date or not end_date:
        return Response({"error": "Start date and end date are required."}, status=400)

    # Query to get total sales for each day in the specified date range
    sales_data = (
        Order.objects.filter(
            order_date_created__date__gte=start_date,
            order_date_created__date__lte=end_date,
            order_status="Paid",
        )
        .values("order_date_created__date")
        .annotate(total_sales=Sum("order_amount"))
        .order_by("order_date_created__date")
    )

    # Prepare the response data
    response_data = {
        entry["order_date_created__date"].isoformat(): entry["total_sales"]
        for entry in sales_data
    }

    return Response(response_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_monthly_products_sold(request):
    year = request.GET.get("year")
    month = request.GET.get("month")

    if year and month:
        # Get the total sold for each product in the specified month and year
        sold_products = (
            OrderItem.objects.filter(
                order__order_date_created__year=year,
                order__order_date_created__month=month,
                order__order_status="Paid",  # Ensure only paid orders are counted
            )
            .select_related("product")  # Fetch related product data
            .values(
                "product__product_id",  # Get product IDs
                "product__product_image",
                "product__product_name",
                "product__product_color",
                "product__product_size",
            )
            .annotate(total_sold=Sum("order_item_quantity"))  # Sum quantities sold
        )

        # Create a list of products with their sold quantities and images
        response_data = [
            {
                "product_id": item["product__product_id"],
                "product_image": item["product__product_image"],
                "product_name": item["product__product_name"],
                "quantity": item["total_sold"],
                "product_color": item["product__product_color"],
                "product_size": item["product__product_size"],
            }
            for item in sold_products
        ]

        return Response(response_data)

    return Response({"error": "Year and month must be provided."}, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sales_by_category(request):
    # Get the selected year from the query parameters (default to current year if not provided)
    selected_year = request.query_params.get("year", None)

    # Get sales data for orders with status "Paid" and the selected year
    sales_data = (
        OrderItem.objects.filter(
            order__order_status="Paid",
            order__order_date_created__year=selected_year,  # Filter by selected year
        )
        .values("product__sub_category__main_category__main_category_name")
        .annotate(total_sales=Sum(F("product_price") * F("order_item_quantity")))
    )

    # Prepare response data
    response_data = {
        entry["product__sub_category__main_category__main_category_name"]: entry[
            "total_sales"
        ]
        for entry in sales_data
    }

    return Response(response_data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def clear_sales_data(request):
    try:
        # Clear all order items
        OrderItem.objects.all().delete()

        # Clear all orders
        Order.objects.all().delete()

        # Reset product_sold for all products to 0
        Product.objects.update(product_sold=0)

        return Response(status=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def clear_customer_data(request):
    try:
        # Clear all customer records
        Customer.objects.all().delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def ping(request):
    return Response({"status": "Backend is operational."}, status=status.HTTP_200_OK)


class VATSettingView(APIView):

    def get(self, request):
        vat_setting = VATSetting.objects.first()
        if not vat_setting:
            return Response(
                {"error": "VAT setting not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = VATSettingSerializer(vat_setting)
        return Response(serializer.data)

    def put(self, request):
        vat_setting, created = VATSetting.objects.get_or_create()
        serializer = VATSettingSerializer(vat_setting, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_sales_data_whole_year(request):
    year = request.GET.get("year", timezone.now().year)

    # Monthly sales data
    monthly_sales = (
        Order.objects.filter(order_date_created__year=year, order_status="Paid")
        .annotate(month=ExtractMonth("order_date_created"))
        .values("month")
        .annotate(total=Sum("order_amount"))
        .order_by("month")
    )

    # Daily sales data
    daily_sales = (
        Order.objects.filter(order_date_created__year=year, order_status="Paid")
        .annotate(date=TruncDate("order_date_created"))
        .values("date")
        .annotate(total=Sum("order_amount"))
        .order_by("date")
    )

    # Paid orders with product names, colors, sizes, and types for the selected year
    paid_orders = (
        Order.objects.filter(order_status="Paid")
        .prefetch_related(
            Prefetch(
                "orderitem_set", queryset=OrderItem.objects.select_related("product")
            )
        )
        .filter(order_id__startswith=str(year))  # Filter by year in order_id
        .values(
            "order_id",
            "order_amount",
            "orderitem__product__product_name",
            "orderitem__product__product_type",
            "orderitem__product__product_color",
            "orderitem__product__product_size",
        )
    )

    # Prepare the response data for paid orders
    paid_orders_data = []
    for order in paid_orders:
        paid_orders_data.append(
            {
                "order_id": order["order_id"],
                "amount": order["order_amount"],
                "product_name": order["orderitem__product__product_name"],
                "product_type": order["orderitem__product__product_type"],
                "color": order["orderitem__product__product_color"],
                "size": order["orderitem__product__product_size"],
            }
        )

    # Products sold data for the selected year
    products_sold = (
        OrderItem.objects.filter(
            order__order_status="Paid", order__order_id__startswith=str(year)
        )
        .values(
            "product__product_name",
            "product__product_type",
            "product__product_color",
            "product__product_size",
        )
        .annotate(total_sold=Sum("order_item_quantity"))
    )

    # Prepare products sold data
    products_sold_data = []
    for product in products_sold:
        products_sold_data.append(
            {
                "name": product["product__product_name"],
                "product_type": product["product__product_type"],
                "color": product["product__product_color"],
                "size": product["product__product_size"],
                "totalSold": product["total_sold"],
            }
        )

    return Response(
        {
            "monthlySales": monthly_sales,
            "dailySales": daily_sales,
            "paidOrders": paid_orders_data,
            "productsSold": products_sold_data,
        }
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_order_item(request, order_id):
    try:
        order = Order.objects.get(order_id=order_id)
        items_data = request.data.get("items", [])

        for item_data in items_data:
            order_item_id = item_data.get("order_item_id")
            new_quantity = item_data.get("quantity")
            discounted_price = item_data.get("discounted_price")

            if order_item_id is None:
                return Response(
                    {"error": "Order item ID is missing from the request data."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if new_quantity is None:
                return Response(
                    {"error": "Quantity is missing from the request data."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                order_item = OrderItem.objects.get(
                    order=order,
                    order_item_id=order_item_id,
                )
            except OrderItem.DoesNotExist:
                return Response(
                    {
                        "error": f"Order item with ID {order_item_id} not found in order {order_id}."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            order_item.order_item_quantity = new_quantity
            if discounted_price is not None:
                order_item.discounted_price = discounted_price
            else:
                order_item.discounted_price = (
                    None  # Set discounted_price to None if it's not provided
                )
            order_item.save()

        # Update the order amount
        order_items = OrderItem.objects.filter(order=order)
        new_amount = sum(
            (
                item.discounted_price
                if item.discounted_price is not None
                else item.product_price
            )
            * item.order_item_quantity
            for item in order_items
        )
        order.order_amount = new_amount
        order.save()

        return Response(
            {"message": "Order item updated successfully."}, status=status.HTTP_200_OK
        )

    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error: {str(e)}")  # Log the error for debugging
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_order_amount(request, order_id):
    try:
        order = Order.objects.get(order_id=order_id)
        new_amount = request.data.get("order_amount")

        if new_amount is None:
            return Response(
                {"error": "Order amount is missing from the request data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.order_amount = new_amount
        order.save()

        return Response(
            {"message": "Order amount updated successfully."}, status=status.HTTP_200_OK
        )

    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error: {str(e)}")  # Log the error for debugging
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cashier_transactions(request):
    # Group orders by cashier
    cashiers = Order.objects.values("order_cashier").distinct()
    transactions = []

    for cashier in cashiers:
        cashier_name = cashier["order_cashier"]
        orders = Order.objects.filter(order_cashier=cashier_name).order_by(
            "-order_date_created"
        )
        order_data = []

        for order in orders:
            order_items = OrderItem.objects.filter(order=order)
            order_data.append(
                {
                    "order_id": order.order_id,
                    "order_date_created": order.order_date_created,
                    "order_status": order.order_status,
                    "order_items": OrderItemHistorySerializer(
                        order_items, many=True, context={"request": request}
                    ).data,
                }
            )

        transactions.append(
            {
                "cashier_name": cashier_name,
                "orders": order_data,
            }
        )

    return Response(transactions)
