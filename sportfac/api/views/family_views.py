from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import filters, generics, mixins, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from registrations.models import Child, ChildActivityLevel
from ..permissions import FamilyPermission, InstructorPermission, IsAuthenticated, ManagerPermission
from ..serializers import ChildActivityLevelSerializer, ChildrenSerializer, SimpleChildrenSerializer


class FamilyView(mixins.ListModelMixin, generics.GenericAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = ChildrenSerializer
    model = Child

    def get_queryset(self):
        user = self.request.user
        return Child.objects.filter(family=user).select_related("teacher", "school", "school_year")

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class FetchPermission(FamilyPermission):
    def has_permission(self, request, view):
        if view.action == "fetch_ext_id":
            return True
        return super().has_permission(request, view)


class ChildActivityLevelViewSet(viewsets.ModelViewSet):
    model = ChildActivityLevel
    queryset = ChildActivityLevel.objects.all()
    permission_classes = (InstructorPermission,)
    serializer_class = ChildActivityLevelSerializer

    def get_object(self):
        """
        Returns the object the view is displaying.
        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg in self.kwargs:
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        else:
            assert "activity" in self.request.data, "expected activity id in payload"
            assert "child" in self.request.data, "expected child id in payload"
            filter_kwargs = {
                "activity__id": self.request.data["activity"],
                "child__id": self.request.data["child"],
            }

        obj = get_object_or_404(queryset, **filter_kwargs)
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid() and "non_field_errors" in serializer.errors:
            # non_field_errors: we are in a duplicate state (a level already exists for same child
            return self.update(request, *args, **kwargs)
        return super().create(request, *args, **kwargs)


class SearchChildThrottle(UserRateThrottle):
    rate = "10/minute"


class ChildrenViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (FetchPermission,)
    serializer_class = ChildrenSerializer
    model = Child

    def get_queryset(self):
        return (
            Child.objects.filter(Q(family=None) | Q(family=self.request.user))
            .prefetch_related("school_year")
            .select_related("teacher")
        )

    # noinspection PyUnusedLocal
    @action(detail=False, methods=["get"], throttle_classes=[SearchChildThrottle])
    def fetch_ext_id(self, request, *args, **kwargs):
        queryset = Child.objects.none()
        params = {}
        if settings.KEPCHUP_LOOKUP_LAGAPEO:
            ext_id = self.request.query_params.get("ext", None)
            if ext_id is not None:
                try:
                    params["id_lagapeo"] = int(ext_id)
                except ValueError:
                    pass
        elif settings.KEPCHUP_LOOKUP_AVS:
            ext_id = self.request.query_params.get("avs", None)
            if ext_id is not None:
                params["avs"] = ext_id

        if params:
            params["is_blacklisted"] = False
            queryset = Child.objects.filter(**params)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        params = {}
        if settings.KEPCHUP_LOOKUP_LAGAPEO:
            ext_id = self.request.query_params.get("ext", None)
            if ext_id is not None:
                try:
                    params["id_lagapeo"] = int(ext_id)
                except ValueError:
                    pass
        elif settings.KEPCHUP_LOOKUP_AVS:
            ext_id = self.request.query_params.get("avs", None)
            if ext_id is not None:
                params["avs"] = ext_id

        if params:
            params["is_blacklisted"] = False
            queryset = Child.objects.filter(**params)
        else:
            queryset = queryset.filter(family=request.user)

        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        if "ext_id" in data and not data["ext_id"]:
            del data["ext_id"]
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.validated_data["family"] = request.user
            if serializer.validated_data.get("school", None) and "other_school" in serializer.validated_data:
                del serializer.validated_data["other_school"]
            try:
                # noinspection PyAttributeOutsideInit
                self.object = serializer.save()
            except IntegrityError:
                return Response("Child already exist", status=status.HTTP_400_BAD_REQUEST)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer):
        serializer.validated_data["family"] = self.request.user
        if "ext_id" in serializer.validated_data:
            del serializer.validated_data["ext_id"]
        if serializer.validated_data.get("school", None):
            serializer.validated_data["other_school"] = ""
        serializer.validated_data["status"] = Child.STATUS.updated
        serializer.save()

    def perform_destroy(self, instance: Child):
        instance.family = None
        instance.emergency_number = ""
        instance.school_year = None
        instance.teacher = None
        instance.school = None
        instance.save()


class SimpleChildrenViewSet(viewsets.ReadOnlyModelViewSet):
    model = Child
    permission_classes = (ManagerPermission,)
    serializer_class = SimpleChildrenSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ("first_name", "last_name")
