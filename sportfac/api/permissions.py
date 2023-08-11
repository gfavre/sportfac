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


class PostfinanceIPFilterPermission(permissions.BasePermission):
    allowed_ips = [
        "52.211.247.160",
        "52.211.171.77",
        "52.211.239.229",
        "52.211.209.173",
        "52.208.210.84",
        "52.212.109.85",
        "52.210.89.1",
        "52.212.185.152",
        "52.212.192.130",
    ]

    def has_permission(self, request, view):
        user_ip = self.get_client_ip(request)
        return user_ip in self.allowed_ips

    # noinspection PyMethodMayBeStatic
    def get_client_ip(self, request):
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR")
