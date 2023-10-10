from django.utils.timezone import now
from django.views.generic import TemplateView

from braces.views import LoginRequiredMixin

from sportfac.views import NotReachableException, WizardMixin

from ..models import Appointment, AppointmentSlot, AppointmentType


class SlotsView(TemplateView):
    template_name = "appointments/slots.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = AppointmentSlot.objects.filter(start__gte=now())
        context["types"] = AppointmentType.objects.all()
        if qs.exists():
            context["start"] = qs.first().start.date().isoformat()
        else:
            context["start"] = now().date().isoformat()
        context["missing_appointments"] = self.request.user.montreux_missing_appointments
        context["appointments"] = (
            self.request.user.is_authenticated
            and Appointment.objects.filter(family=self.request.user, slot__in=qs)
            or Appointment.objects.none()
        )
        available_dates = []
        if AppointmentType.objects.exists():
            for appointment_type in AppointmentType.objects.all():
                available_dates.append(
                    [
                        appointment_type.label,
                        sorted(
                            {
                                d.date()
                                for d in qs.values_list("start", flat=True)
                                if appointment_type.start <= d <= appointment_type.end
                            }
                        ),
                    ]
                )
        else:
            available_dates = ["", sorted({d.date() for d in qs.values_list("start", flat=True)})]
        context["available_dates"] = available_dates
        return context


class SuccessfulRegister(TemplateView):
    """User is not logged in we can't link the appointments juste created. Let's just tell him it worked."""

    template_name = "appointments/success.html"


class WizardSlotsView(LoginRequiredMixin, WizardMixin, SlotsView):
    template_name = "appointments/wizard_register.html"

    @staticmethod
    def check_initial_condition(request):
        if not request.user.is_authenticated:
            raise NotReachableException("No account created")
        if not request.user.montreux_missing_appointments:
            raise NotReachableException("No appointment expected")
