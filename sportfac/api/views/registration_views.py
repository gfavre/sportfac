from profiles.models import SchoolYear
from registrations.models import ExtraInfo, Registration
from rest_framework import status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from schools.models import Building, Teacher

from ..permissions import ChildOrAdminPermission, RegistrationOwnerAdminPermission
from ..serializers import (
    BuildingSerializer,
    ExtraSerializer,
    RegistrationSerializer,
    TeacherSerializer,
    YearSerializer,
)


class BuildingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BuildingSerializer
    model = Building
    queryset = Building.objects.all()


class ExtraInfoViewSet(viewsets.ModelViewSet):
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
                data["key"] = key.split("-")[1]
                data["value"] = value
                if request.data.get("image", None):
                    data["image"] = request.data.get("image")

                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                output.append(serializer.data)

        return Response(output, status=status.HTTP_201_CREATED)


class RegistrationViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (ChildOrAdminPermission,)
    serializer_class = RegistrationSerializer
    model = Registration

    def get_queryset(self):
        user = self.request.user
        return Registration.objects.filter(child__in=user.children.all())

    def create(self, request, *args, **kwargs):
        if type(request.data) is list:
            data = []
            errors = []
            self.get_queryset().exclude(validated=True).exclude(paid=True).delete()
            for registration in request.data:
                serializer = RegistrationSerializer(data=registration)
                if serializer.is_valid():
                    serializer.save()
                    data.append(serializer.data)
                else:
                    errors.append(serializer.errors)
            if data:
                return Response(data, status=status.HTTP_201_CREATED)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeacherViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TeacherSerializer
    model = Teacher

    def get_queryset(self):
        return Teacher.objects.prefetch_related("years")


class YearViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = YearSerializer
    model = SchoolYear
    queryset = SchoolYear.visible_objects.all()
