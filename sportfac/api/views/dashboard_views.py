from datetime import timedelta

from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from profiles.models import FamilyUser
from registrations.models import Registration
from rest_framework import generics
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework_datatables.pagination import DatatablesPageNumberPagination
from rest_framework_datatables.renderers import DatatablesRenderer

from ..filters import DatatablesFilterandPanesBackend
from ..serializers import FamilySerializer, InstructorSerializer


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

    def get_queryset(self):
        qs = super().get_queryset()
        user: FamilyUser = self.request.user
        if user.is_restricted_manager:
            registrations = Registration.objects.filter(course__activity__in=user.managed_activities.all())
            return qs.filter(children__registrations__in=registrations).distinct()
        return qs

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
