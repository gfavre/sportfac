# -*- coding: utf-8 -*-
from datetime import timedelta
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now

from rest_framework import generics
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework_datatables.pagination import DatatablesPageNumberPagination
from rest_framework_datatables.renderers import DatatablesRenderer

from profiles.models import FamilyUser
from ..serializers import FamilySerializer, InstructorSerializer
from ..filters import DatatablesFilterandPanesBackend


class DashboardFamilyView(generics.ListAPIView):
    filter_backends = (DatatablesFilterandPanesBackend,)
    pagination_class = DatatablesPageNumberPagination
    queryset = FamilyUser.active_objects.prefetch_related('children').select_related('profile')
    renderer_classes = (BrowsableAPIRenderer, DatatablesRenderer,)
    serializer_class = FamilySerializer

    class Meta:
        """Meta class for viewset."""
        datatables_extra_json = ('get_search_panes',)

    def get_search_panes(self):
        return 'searchPanes', {
            "options": {
                "finished_registrations": [
                    {
                        'label': _("Has finished registering"),
                        'value': 1,
                        'count': 0,
                        'total': FamilyUser.objects.filter(profile__finished_registering=True).count()
                    },
                    {
                        'label': _("Has not finished registering"),
                        'value': 0,
                        'count': 0,
                        'total': FamilyUser.objects.filter(profile__finished_registering=False).count()
                    },
                ],

                "last_registration": [
                    {
                        'label': _("Has registrations"),
                        'value': self.request.REGISTRATION_START,
                        'count': 0,
                        'total': FamilyUser.objects.exclude(profile__last_registration=None).count()
                    },
                    {
                        'label': _("Has no registration"),
                        'value': now() + timedelta(days=366),
                        'count': 0,
                        'total': FamilyUser.objects.filter(profile__last_registration=None).count()
                    },
                ],

                "has_paid": [
                    {
                        'label': _("Has paid"),
                        'value': 1,
                        'count': 0,
                        'total': FamilyUser.objects.filter(profile__has_paid_all=True).count()
                    },
                    {
                        'label': _("Has not paid"),
                        'value': 0,
                        'count': 0,
                        'total': FamilyUser.objects.filter(profile__has_paid_all=False).count()
                    },
                ]

            }
        }


class DashboardInstructorsView(DashboardFamilyView):
    queryset = FamilyUser.instructors_objects.prefetch_related('course', 'course__activity')
    serializer_class = InstructorSerializer

    class Meta:
        datatables_extra_json = ()


class DashboardManagersView(DashboardFamilyView):
    queryset = FamilyUser.managers_objects.all()

    class Meta:
        datatables_extra_json = ()
