from .activity_views import *
from .allocation_views import (
    AllocationAccountCreateView,
    AllocationAccountDeleteView,
    AllocationAccountListView,
    AllocationAccountReportView,
    AllocationAccountUpdateView,
)
from .course_views import *
from .dashboard_views import *
from .mail_views import *
from .payroll_views import (
    FunctionCreateView,
    FunctionDeleteView,
    FunctionListView,
    FunctionUpdateView,
    PayrollReportView,
    SupervisorRolesList,
)
from .registration_views import *
from .site_views import (
    AppointmentDeleteView,
    AppointmentsExportView,
    AppointmentsListView,
    AppointmentsManagementView,
    FlatPageListView,
    FlatPageUpdateView,
    GenericEmailListView,
    GenericEmailUpdateView,
)
from .teacher_views import *
from .user_views import *
from .waiting_slots_views import WaitingSlotDeleteView, WaitingSlotTransformView
from .year_views import *
