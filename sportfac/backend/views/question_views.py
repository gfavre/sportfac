from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView
from django.views.generic import TemplateView

from activities.forms import CourseQuestionsField
from activities.models import ExtraNeed
from backend.question_forms import QuestionForm
from registrations.models import ExtraInfo

from .mixins import FullBackendMixin


class QuestionListView(FullBackendMixin, ListView):
    template_name = "backend/questions/list.html"
    context_object_name = "questions"

    def get_queryset(self):
        queryset = (
            ExtraNeed.objects.annotate(answer_count=Count("extrainfo", distinct=True))
            .prefetch_related("courses")
            .order_by("question_label", "pk")
        )
        query = self.request.GET.get("q", "").strip()
        return queryset.filter(question_label__icontains=query) if query else queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        field = CourseQuestionsField(queryset=ExtraNeed.objects.none())
        for question in context["questions"]:
            question.summary = field.label_from_instance(question)
        return context


class QuestionEditView(FullBackendMixin, TemplateView):
    template_name = "backend/questions/form.html"
    duplicate = False

    def get_question(self, lock=False):
        if "pk" not in self.kwargs:
            return ExtraNeed()
        queryset = ExtraNeed.objects.select_for_update() if lock else ExtraNeed.objects
        return get_object_or_404(queryset, pk=self.kwargs["pk"])

    def make_form(self, question, data=None):
        if self.duplicate:
            # A copy is deliberately unattached: no live course is changed by opening or saving it.
            question = ExtraNeed(
                question_label=question.question_label,
                extra_info=question.extra_info,
                type=question.type,
                mandatory=question.mandatory,
                image_label=question.image_label,
                default=question.default,
                choices=list(question.choices or []),
                price_modifier=list(question.price_modifier or []),
            )
            initial = {}
            if question.type in ("B", "IM"):
                initial = {"no_price": question.price_dict.get("0", 0), "yes_price": question.price_dict.get("1", 0)}
            return QuestionForm(data, instance=question, initial=initial)
        return QuestionForm(data, instance=question)

    def render_form(self, form, question):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                question=question,
                duplicate=self.duplicate,
                affected_courses=question.courses.all() if question.pk and not self.duplicate else [],
            )
        )

    def get(self, request, *args, **kwargs):
        question = self.get_question()
        return self.render_form(self.make_form(question), question)

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            question = self.get_question(lock=True)
            data = request.POST.copy()
            if data.get("action") == "edit":
                data.pop("confirm_changes", None)
            form = self.make_form(question, data)
            if data.get("action") == "edit":
                form.is_valid()
                form.errors.pop("confirm_changes", None)
                return self.render_form(form, question)
            if form.is_valid():
                form.save()
                messages.success(request, _("Registration question saved."))
                return HttpResponseRedirect(reverse("backend:question-list"))
            if set(form.errors) == {"confirm_changes"}:
                return TemplateResponse(
                    request,
                    "backend/questions/confirm.html",
                    self.get_context_data(
                        question=question,
                        changes=form.configuration_changes(),
                        answer_count=form.answer_count,
                        selected_courses=form.cleaned_data["courses"],
                        submitted_fields=[
                            (name, value)
                            for name, values in data.lists()
                            if name not in ("csrfmiddlewaretoken", "confirm_changes", "action")
                            for value in values
                        ],
                    ),
                )
            return self.render_form(form, question)


class QuestionDeleteView(FullBackendMixin, TemplateView):
    template_name = "backend/questions/delete.html"

    def get(self, request, *args, **kwargs):
        question = get_object_or_404(ExtraNeed, pk=kwargs["pk"])
        return self.render_to_response(
            self.get_context_data(
                question=question,
                has_answers=ExtraInfo.objects.filter(key=question).exists(),
            )
        )

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            question = get_object_or_404(ExtraNeed.objects.select_for_update(), pk=kwargs["pk"])
            if ExtraInfo.objects.filter(key=question).exists():
                messages.error(request, _("This question has answers and cannot be deleted."))
            else:
                question.delete()
                messages.success(request, _("Registration question deleted."))
        return HttpResponseRedirect(reverse("backend:question-list"))
