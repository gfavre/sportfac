from .activity_views import *
from .allocation_views import (
    AllocationAccountListView, AllocationAccountCreateView, AllocationAccountDeleteView, AllocationAccountUpdateView,
    AllocationAccountReportView)
from .course_views import *
from .dashboard_views import *
from .mail_views import *
from .registration_views import *
from .teacher_views import *
from .user_views import *
from site_views import (FlatPageListView, FlatPageUpdateView, AppointmentDeleteView, AppointmentsListView,
                        AppointmentsManagementView, AppointmentsExportView,
                        GenericEmailListView, GenericEmailUpdateView)
from .year_views import *
from .waiting_slots_views import WaitingSlotTransformView

