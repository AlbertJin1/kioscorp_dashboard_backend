from rest_framework.permissions import BasePermission
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow users to edit their own profiles.
    """

    def has_object_permission(self, request, view, obj):
        # Allow access only to the owner of the object
        return obj == request.user


# Custom permission class to allow Owner to access or modify users

class IsOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['owner', 'admin']

    def has_object_permission(self, request, view, obj):
        # Owner can edit or delete users, just like admin
        return request.user.role in ['owner', 'admin']
