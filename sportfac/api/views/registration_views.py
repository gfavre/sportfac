import logging

from rest_framework import status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response

from profiles.models import SchoolYear
from registrations.models import ExtraInfo, Registration
from schools.models import Building, Teacher
from ..permissions import ChildOrAdminPermission, RegistrationOwnerAdminPermission
from ..serializers import (
    BuildingSerializer,
    ExtraInfoSerializer,
    ExtraSerializer,
    RegistrationSerializer,
    TeacherSerializer,
    YearSerializer,
)


logger = logging.getLogger(__name__)


class BuildingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BuildingSerializer
    model = Building
    queryset = Building.objects.all()


class OldExtraInfoViewSet(viewsets.ModelViewSet):
    # DEPRECATED
    authentication_classes = (SessionAuthentication,)
    permission_classes = (RegistrationOwnerAdminPermission,)
    serializer_class = ExtraSerializer
    model = ExtraInfo

    def get_queryset(self):
        user = self.request.user
        return ExtraInfo.objects.filter(registration__child__in=user.children.all())

    def create(self, request, *args, **kwargs):
        base_data = {"registration": request.data.get("registration", None)}
        output = []

        for key, value in request.data.items():
            if key.startswith("extra-") and value:
                data = base_data.copy()
                try:
                    data["key"] = key.split("-")[1]
                    data["value"] = value
                    if request.data.get("image", None):
                        data["image"] = request.data.get("image")

                    serializer = self.get_serializer(data=data)
                    serializer.is_valid(raise_exception=True)
                    self.perform_create(serializer)
                    output.append(serializer.data)
                except Exception as e:
                    logger.error(f"error with extra infos {data}", exc_info=e)
                    continue

        return Response(output, status=status.HTTP_201_CREATED)


class ExtraInfoViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)

    queryset = ExtraInfo.objects.all()
    serializer_class = ExtraInfoSerializer

    def get_queryset(self):
        """Limit queryset to ExtraInfo objects owned by the logged-in user."""
        user = self.request.user
        if user.is_authenticated:
            return ExtraInfo.objects.filter(registration__child__family=user)
        return ExtraInfo.objects.none()  # Return an empty queryset if user is not authenticated

    def create(self, request, *args, **kwargs):
        """Handle create requests."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "extra_info_id": serializer.instance.pk, "message": "Created successfully."},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "errors": serializer.errors, "message": "Validation failed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def update(self, request, *args, **kwargs):
        """Handle update requests."""
        instance = self.get_object()
        if instance.registration.child.family != request.user:
            return Response(
                {"success": False, "message": "You do not have permission to update this resource."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data.copy()
        # If image is not included in the request data, retain the existing image
        if "image" not in request.FILES:
            data["image"] = instance.image

        serializer = self.get_serializer(instance, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "extra_info_id": serializer.instance.pk, "message": "Updated successfully."},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"success": False, "errors": serializer.errors, "message": "Update failed."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class RegistrationViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (ChildOrAdminPermission,)
    serializer_class = RegistrationSerializer
    model = Registration

    def get_queryset(self):
        user = self.request.user
        return Registration.objects.filter(child__in=user.children.all())


class TeacherViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TeacherSerializer
    model = Teacher

    def get_queryset(self):
        return Teacher.objects.prefetch_related("years")


class YearViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = YearSerializer
    model = SchoolYear
    queryset = SchoolYear.visible_objects.all()
