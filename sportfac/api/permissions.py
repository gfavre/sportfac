from rest_framework import permissions

class ManagerPermission(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_manager:
            return True
        return False


class FamilyOrAdminPermission(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_manager or request.user == obj.family or obj.family == None:
            return True
        return False

class FamilyPermission(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user == obj.family or obj.family == None:
            return True
        return False


class ResponsiblePermission(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_manager or request.user.is_staff or request.user.is_superuser:
            return True
        return obj.course.responsible == request.user
    