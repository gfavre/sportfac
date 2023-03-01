# -*- coding:utf-8 -*-
from rest_framework import permissions


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class ManagerPermission(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.user.is_manager or request.user.is_staff


class FamilyOrAdminPermission(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_manager or request.user == obj.family or obj.family is None:
            return True
        return False


class FamilyPermission(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user == obj.family or obj.family is None:
            return True
        return False


class InstructorPermission(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_manager or request.user.is_staff or request.user.is_superuser:
            return True
        try:
            return request.user in obj.course.instructors.all()
        except AttributeError:
            # activitylevel => has no course element
            return request.user.is_instructor


class RegistrationOwnerAdminPermission(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_manager or request.user == obj.registration.child.family:
            return True
        return False


class ChildOrAdminPermission(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_manager or request.user == obj.child.family:
            return True
        return False
