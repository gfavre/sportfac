import json

from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from activities.models import Course
from activities.models import ExtraNeed
from registrations.models import Child
from registrations.models import ExtraInfo
from registrations.models import Registration
from registrations.models import Transport

from .mixins import FullBackendMixin


class TransportStopsForm(forms.ModelForm):
    stop_values = forms.MultipleChoiceField(
        label=_("Arrêts desservis"), required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Transport
        fields = ("stop_question", "stop_values")

    def __init__(self, *args, question=None, values=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["stop_question"].widget = forms.HiddenInput()
        self.fields["stop_question"].queryset = (
            ExtraNeed.objects.filter(pk=question.pk) if question else ExtraNeed.objects.none()
        )
        self.fields["stop_values"].choices = [(value, value) for value in values]
        self.initial["stop_question"] = question.pk if question else None
        if self.instance.stop_question_id != (question.pk if question else None):
            self.initial["stop_values"] = []


class TransportAssignmentForm(forms.Form):
    children = forms.ModelMultipleChoiceField(queryset=Child.objects.none(), widget=forms.CheckboxSelectMultiple)
    destination = forms.ModelChoiceField(
        label=_("Car de destination"), queryset=Transport.objects.order_by("name", "pk")
    )

    def __init__(self, *args, child_ids=(), destination=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["children"].queryset = Child.objects.filter(pk__in=child_ids)
        self.fields["destination"].widget.attrs["class"] = "form-control"
        self.initial["destination"] = destination


class TransportAssignmentView(FullBackendMixin, TemplateView):
    template_name = "backend/registration/transport-assignments.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transport = get_object_or_404(Transport, pk=self.kwargs["pk"]) if "pk" in self.kwargs else None
        questions = ExtraNeed.objects.order_by("question_label", "pk")
        question_id = self.request.GET.get("question")
        if question_id:
            question = get_object_or_404(questions, pk=question_id) if question_id.isdigit() else None
        else:
            question = (
                transport.stop_question
                if transport and transport.stop_question_id
                else questions.filter(question_label__istartswith="Arr").first()
            )
        by_child, values = self.get_stop_data(question, transport)
        stop = self.request.GET.get("stop", "")
        car = self.request.GET.get("car", "current" if transport else "all")
        search = self.request.GET.get("q", "").strip()
        selected_courses = self.request.GET.getlist("course")
        served = (
            transport.stop_values
            if transport and transport.stop_question_id == (question.pk if question else None)
            else []
        )
        table_children = self.get_children(by_child)
        child_id = self.request.GET.get("child")
        if child_id:
            table_children = [entry for entry in table_children if str(entry["child"].pk) == child_id]
        rows = self.filter_children(table_children, stop, car, search, transport, served)
        if selected_courses:
            rows = [entry for entry in rows if set(selected_courses).intersection(entry["course_ids"])]
        context.update(
            transport=transport,
            questions=questions,
            question=question,
            stop=stop,
            car=car,
            search=search,
            selected_courses=selected_courses,
            courses=Course.objects.filter(pk__in=Registration.objects.values("course_id"))
            .select_related("activity")
            .order_by("number", "pk"),
            stop_values=sorted(values),
            children=rows,
            table_children=table_children,
            served_stops=served,
            selected_children=self.request.POST.getlist("children"),
            from_bibs=self.request.GET.get("from") == "bibs",
            transports=Transport.objects.order_by("name", "pk"),
        )
        context.setdefault(
            "assignment_form",
            TransportAssignmentForm(child_ids=[entry["child"].pk for entry in rows], destination=transport),
        )
        if transport:
            context.setdefault(
                "stops_form", TransportStopsForm(instance=transport, question=question, values=sorted(values))
            )
        return context

    def get_stop_data(self, question, transport):
        by_child = {}
        values = set(question.choices or []) if question else set()
        if question:
            answers = ExtraInfo.objects.filter(key=question, registration__in=Registration.objects.all()).values_list(
                "registration__child_id", "value"
            )
            for child_id, value in answers:
                if value:
                    by_child.setdefault(child_id, set()).add(value)
                    values.add(value)
        if transport and transport.stop_question_id == (question.pk if question else None):
            values.update(transport.stop_values)
        return by_child, sorted(values)

    @staticmethod
    def matches_stop(stops, stop, served):
        if stop == "__missing__":
            return not stops
        if stop == "__served__":
            return bool(set(stops).intersection(served))
        return not stop or stop in stops

    def get_children(self, by_child):
        children = {}
        for registration in Registration.objects.select_related(
            "child", "transport", "course", "course__activity"
        ).order_by("child__last_name", "child__first_name", "child_id", "pk"):
            entry = children.setdefault(
                registration.child_id,
                {
                    "child": registration.child,
                    "cars": {},
                    "courses": {},
                    "stops": sorted(by_child.get(registration.child_id, set())),
                },
            )
            entry["cars"][registration.transport_id] = registration.transport
            entry["courses"][registration.course_id] = registration.course
        for entry in children.values():
            entry["course_ids"] = [str(pk) for pk in entry["courses"]]
            entry["courses_json"] = json.dumps(entry["course_ids"])
            entry["courses"] = sorted(entry["courses"].values(), key=lambda course: (course.number, course.pk))
            entry["pending"] = (
                None in entry["cars"]
                or len(entry["cars"]) > 1
                or any(car.bib_prefix is None for car in entry["cars"].values() if car)
            )
            entry["car_ids"] = list(entry["cars"])
            entry["stops_json"] = json.dumps(entry["stops"])
            entry["cars_json"] = json.dumps([str(pk) if pk else "none" for pk in entry["cars"]])
            entry["cars"] = list(entry["cars"].values())
        return list(children.values())

    def filter_children(self, children, stop, car, search, transport, served):
        rows = []
        for entry in children:
            if car == "pending" and not entry["pending"]:
                continue
            if not self.matches_stop(entry["stops"], stop, served):
                continue
            if not self.matches_car(entry["car_ids"], car, transport):
                continue
            child = entry["child"]
            if search and search.casefold() not in f"{child.last_name} {child.first_name}".casefold():
                continue
            rows.append(entry)
        return rows

    @staticmethod
    def matches_car(cars, car, transport):
        if car == "none":
            return None in cars
        if car == "current":
            return transport is not None and transport.pk in cars
        return not car.isdigit() or int(car) in cars

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        if request.POST.get("action") == "stops" and context["transport"]:
            form = TransportStopsForm(
                request.POST,
                instance=context["transport"],
                question=context["question"],
                values=context["stop_values"],
            )
            if form.is_valid():
                form.save()
                messages.success(request, _("Arrêts desservis enregistrés."))
                return HttpResponseRedirect(request.get_full_path())
            context["stops_form"] = form
        else:
            form = TransportAssignmentForm(
                request.POST, child_ids=[entry["child"].pk for entry in context["children"]]
            )
            if form.is_valid():
                with transaction.atomic():
                    # Same lock order as bib generation; transport changes never call Registration.save().
                    destination = get_object_or_404(
                        Transport.objects.select_for_update(), pk=form.cleaned_data["destination"].pk
                    )
                    registrations = (
                        Registration.objects.select_for_update()
                        .filter(child__in=form.cleaned_data["children"])
                        .order_by("pk")
                    )
                    ids = list(registrations.values_list("pk", flat=True))
                    Registration.objects.filter(pk__in=ids).update(transport=destination, modified=now())
                messages.success(
                    request,
                    _("%(count)s enfant(s) affecté(s) au car %(car)s.")
                    % {
                        "count": len(form.cleaned_data["children"]),
                        "car": destination,
                    },
                )
                return HttpResponseRedirect(request.get_full_path())
            context["assignment_form"] = form
        return self.render_to_response(context)
