from django.conf import settings
from django.http import Http404
from django.utils.timezone import now
from django.views.generic import TemplateView

from braces.views import LoginRequiredMixin

from profiles.models import FamilyUser
from registrations.models import Child
from wizard.views import StaticStepView
from ..forms import RentalSelectionForm
from ..models import Appointment, AppointmentSlot, AppointmentType, Rental


class SlotsBaseView(TemplateView):
    template_name = "appointments/slots.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user: FamilyUser = self.request.user
        qs = AppointmentSlot.objects.filter(start__gte=now())
        context["types"] = AppointmentType.objects.all()
        if qs.exists():
            context["start"] = qs.first().start.date().isoformat()
        else:
            context["start"] = now().date().isoformat()
        context["missing_appointments"] = user.montreux_missing_appointments
        context["appointments"] = (
            user.is_authenticated
            and Appointment.objects.filter(family=user, slot__in=qs)
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


class SlotsView(SlotsBaseView):
    def get(self, request, *args, **kwargs):
        if not settings.KEPCHUP_APPOINTMENTS_WITHOUT_WIZARD:
            raise Http404()
        return super().get(request, *args, **kwargs)


class WizardRentalStepView(LoginRequiredMixin, StaticStepView):
    template_name = "wizard/equipment.html"
    requires_completion = True
    step_slug = "equipment"
    appointment_type = "pickup"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        disabled_children = Child.objects.filter(rentals__isnull=False, rentals__paid=True, family=user)
        children_with_rentals = Child.objects.filter(rentals__isnull=False, rentals__paid=False, family=user)

        context["appointment_type"] = self.appointment_type
        context["rentals"] = Rental.objects.filter(child__family=user, paid=False)
        context["rentals_json"] = [
            {
                "id": rental.id,
                "child": rental.child.id,
                "pickup_appointment": rental.pickup_appointment.slot.id if rental.pickup_appointment else "",
                "return_appointment": rental.return_appointment.slot.id if rental.return_appointment else "",
            }
            for rental in context["rentals"]
        ]

        context["form"] = RentalSelectionForm(
            user=user,
            initial_children=children_with_rentals,
            disabled_children_initial=disabled_children,
            disabled=self.appointment_type != "pickup",
        )
        qs = AppointmentSlot.objects.filter(start__gte=now(), appointment_type=self.appointment_type)
        if qs.exists():
            context["start"] = qs.first().start.date().isoformat()
        else:
            context["start"] = now().date().isoformat()
        context["available_dates"] = sorted({slot.start.date() for slot in qs if slot.start.date() >= now().date()})
        return context

    # def get_success_url(self):
    #    return self.get_next_step_url()


class WizardReturnStepView(WizardRentalStepView):
    template_name = "wizard/equipment.html"
    requires_completion = True
    step_slug = "equipment-return"
    appointment_type = "return"
