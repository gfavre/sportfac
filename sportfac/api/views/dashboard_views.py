from datetime import timedelta

from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from rest_framework import generics
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework_datatables.pagination import DatatablesPageNumberPagination
from rest_framework_datatables.renderers import DatatablesRenderer

from profiles.models import FamilyUser
from registrations.models import Child
from registrations.models import Registration

from ..filters import DatatablesFilterandPanesBackend
from ..serializers import ChildDatatableSerializer
from ..serializers import FamilySerializer
from ..serializers import InstructorSerializer
from ..serializers import RegistrationDatatableSerializer


class DashboardFamilyView(generics.ListAPIView):
    filter_backends = (DatatablesFilterandPanesBackend,)
    pagination_class = DatatablesPageNumberPagination
    queryset = FamilyUser.active_objects.prefetch_related("children").select_related("profile")
    renderer_classes = (
        BrowsableAPIRenderer,
        DatatablesRenderer,
    )
    serializer_class = FamilySerializer

    class Meta:
        datatables_extra_json = ("get_search_panes",)

    def get_search_panes(self):
        return "searchPanes", {
            "options": {
                "finished_registrations": [
                    {
                        "label": _("Has finished registering"),
                        "value": 1,
                        "count": 0,
                        "total": FamilyUser.objects.filter(profile__finished_registering=True).count(),
                    },
                    {
                        "label": _("Has not finished registering"),
                        "value": 0,
                        "count": 0,
                        "total": FamilyUser.objects.filter(profile__finished_registering=False).count(),
                    },
                ],
                "last_registration": [
                    {
                        "label": _("Has registrations"),
                        "value": self.request.REGISTRATION_START,
                        "count": 0,
                        "total": FamilyUser.objects.exclude(profile__last_registration=None).count(),
                    },
                    {
                        "label": _("Has no registration"),
                        "value": now() + timedelta(days=366),
                        "count": 0,
                        "total": FamilyUser.objects.filter(profile__last_registration=None).count(),
                    },
                ],
                "has_paid": [
                    {
                        "label": _("Has paid"),
                        "value": 1,
                        "count": 0,
                        "total": FamilyUser.objects.filter(profile__has_paid_all=True).count(),
                    },
                    {
                        "label": _("Has not paid"),
                        "value": 0,
                        "count": 0,
                        "total": FamilyUser.objects.filter(profile__has_paid_all=False).count(),
                    },
                ],
            }
        }


class DashboardInstructorsView(DashboardFamilyView):
    serializer_class = InstructorSerializer

    class Meta:
        datatables_extra_json = ()

    def get_queryset(self):
        user: FamilyUser = self.request.user
        qs = FamilyUser.instructors_objects.all()
        if user.is_restricted_manager:
            qs = qs.filter(coursesinstructors__course__activity__in=user.managed_activities.all())
        return qs.prefetch_related("children").select_related("profile")


class DashboardManagersView(DashboardFamilyView):
    queryset = FamilyUser.managers_objects.all()

    class Meta:
        datatables_extra_json = ()


class DashboardChildrenView(generics.ListAPIView):
    filter_backends = (DatatablesFilterandPanesBackend,)
    pagination_class = DatatablesPageNumberPagination
    renderer_classes = (
        BrowsableAPIRenderer,
        DatatablesRenderer,
    )
    serializer_class = ChildDatatableSerializer

    class Meta:
        datatables_extra_json = ("get_search_panes",)

    def get_queryset(self):
        user: FamilyUser = self.request.user
        qs = Child.objects.select_related("family", "school_year", "school", "building")
        if user.is_restricted_manager:
            registrations = Registration.objects.filter(course__activity__in=user.managed_activities.all())
            return qs.filter(registrations__in=registrations).distinct()
        return qs

    def get_search_panes(self):
        return "searchPanes", {
            "options": {
                "is_blacklisted": [
                    {
                        "label": _("Blacklisted"),
                        "value": 1,
                        "count": 0,
                        "total": Child.objects.filter(is_blacklisted=True).count(),
                    },
                    {
                        "label": _("Not blacklisted"),
                        "value": 0,
                        "count": 0,
                        "total": Child.objects.filter(is_blacklisted=False).count(),
                    },
                ],
            }
        }


class DashboardRegistrationsView(generics.ListAPIView):
    filter_backends = (DatatablesFilterandPanesBackend,)
    pagination_class = DatatablesPageNumberPagination
    renderer_classes = (
        BrowsableAPIRenderer,
        DatatablesRenderer,
    )
    serializer_class = RegistrationDatatableSerializer

    class Meta:
        datatables_extra_json = ("get_search_panes",)

    def get_queryset(self):
        # Same scoping as backend.views.registration_views.RegistrationMixin -
        # Registration.all_objects (not the default manager) so canceled registrations
        # stay visible here, same as the page this replaces.
        user: FamilyUser = self.request.user
        qs = Registration.all_objects.select_related(
            "course", "course__activity", "child", "child__family", "cancelation_person"
        )
        if user.is_full_manager:
            return qs
        return qs.filter(course__activity__in=user.managed_activities.all())

    def get_search_panes(self):
        qs = self.get_queryset()
        return "searchPanes", {
            "options": {
                "status_display": [
                    {
                        "label": label,
                        "value": value,
                        "count": 0,
                        "total": qs.filter(status=value).count(),
                    }
                    for value, label in Registration.STATUS
                ],
            }
        }
