import mimetypes
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import connection
from django.db import transaction
from django.db.models import Count
from django.db.models import Max
from django.db.models import Q
from django.http import FileResponse
from django.http import Http404
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from dynamic_preferences.registries import global_preferences_registry

from backend.views.mixins import FullBackendMixin
from registrations.models import Registration

from .confirmation import confirmation_matches
from .confirmation import confirmation_token
from .confirmation import mail_counts
from .forms import BatchForm
from .forms import DiplomaForm
from .forms import DiplomaMessageForm
from .models import Diploma
from .models import DiplomaBatch
from .models import DiplomaEvent
from .models import DiplomaSupplement
from .services import complete_missing_levels
from .services import course_mail_history
from .services import create_batch
from .services import separate_draft_courses
from .tasks import generate_batch
from .tasks import render_diplomas
from .tasks import send_batch


class DiplomaEnabledMixin:
    def dispatch(self, request, *args, **kwargs):
        if not settings.KEPCHUP_DIPLOMAS:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


def pdf_response(content, filename):
    response = HttpResponse(bytes(content), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "private, no-store"
    return response


class BatchListView(DiplomaEnabledMixin, FullBackendMixin, View):
    def get(self, request):
        resumable = set(
            DiplomaBatch.objects.filter(source_schema=connection.schema_name, status__in=("draft", "ready", "failed"))
            .exclude(diplomas__mail_status__in=("sent", "sending", "failed"))
            .exclude(diplomas__published_at__isnull=False)
            .values_list("pk", flat=True)
        )
        preparations = (
            Diploma.objects.filter(batch__source_schema=connection.schema_name)
            .values("course_number", "activity", "batch_id", "batch__issued_on", "batch__status", "batch__created")
            .annotate(total=Count("pk"), sent=Count("pk", filter=Q(mail_status="sent")), last_sent=Max("sent_at"))
            .order_by("course_number", "-batch__created")
        )
        courses = {}
        statuses = dict(DiplomaBatch._meta.get_field("status").choices)
        for preparation in preparations:
            course = courses.setdefault(
                preparation["course_number"],
                {
                    "number": preparation["course_number"],
                    "activity": preparation["activity"],
                    "preparations": [],
                    "last_sent": None,
                },
            )
            preparation["status_label"] = statuses[preparation["batch__status"]]
            preparation["can_resume"] = preparation["batch_id"] in resumable
            course["preparations"].append(preparation)
            if preparation["last_sent"] and (
                not course["last_sent"] or preparation["last_sent"] > course["last_sent"]
            ):
                course["last_sent"] = preparation["last_sent"]
        for course in courses.values():
            course["current"] = course["preparations"][0]
            course["history"] = course["preparations"][1:]
        return render(request, "diplomas/batches.html", {"courses": list(courses.values())})


class BatchCreateView(DiplomaEnabledMixin, FullBackendMixin, View):
    def get(self, request):
        year = timezone.localdate().year
        form = BatchForm(
            initial={
                "courses": request.GET.getlist("c"),
                "season": f"Hiver {year}",
                "subject": f"SSF {year} – diplôme de participation de votre enfant",
            }
        )
        return render(request, "diplomas/create.html", {"form": form})

    def post(self, request):
        form = BatchForm(request.POST, request.FILES)
        if form.is_valid():
            batches = []
            with transaction.atomic():
                courses = form.cleaned_data["courses"]
                for course in courses:
                    data = {**form.cleaned_data, "courses": courses.filter(pk=course.pk)}
                    if data.get("supplement"):
                        data["supplement"].seek(0)
                    batches.append(create_batch(data, request.user))
            if len(batches) > 1:
                messages.success(request, "Les diplômes sont prêts à compléter séparément pour chaque cours.")
                return redirect("backend:diploma-list")
            batch = batches[0]
            return redirect("backend:diploma-batch", pk=batch.pk)
        return render(request, "diplomas/create.html", {"form": form})


def queue_generation(batch, send_after=False):
    try:
        generate_batch.delay(str(batch.pk), send_after=send_after)
    except Exception as exc:
        DiplomaBatch.objects.filter(pk=batch.pk).update(status="failed", error="Mise en file impossible : " + str(exc))
        DiplomaEvent.objects.create(batch=batch, action="queue_failed", detail=str(exc))


class BatchStatusView(DiplomaEnabledMixin, FullBackendMixin, View):
    def get(self, request, pk):
        batch = get_object_or_404(DiplomaBatch.objects.only("status"), pk=pk)
        response = JsonResponse({"status": batch.status})
        response["Cache-Control"] = "private, no-store"
        return response


class BatchDetailView(DiplomaEnabledMixin, FullBackendMixin, View):
    def get(self, request, pk):
        batch = get_object_or_404(DiplomaBatch.objects.defer("print_pdf", "logo"), pk=pk)
        complete_missing_levels(batch, request.user)
        queryset = batch.diplomas.select_related("parent").defer("pdf")
        course_scope = request.GET.get("course")
        if course_scope is not None:
            queryset = queryset.filter(course_number=course_scope)
            if not queryset.exists():
                raise Http404
        diplomas = list(queryset)
        # Registration IDs are only meaningful inside the period that created the batch.
        if batch.source_schema == connection.schema_name and settings.KEPCHUP_REGISTRATION_LEVELS:
            children = dict(
                Registration.objects.filter(
                    pk__in=[d.source_registration_id for d in diplomas if not d.evaluation]
                ).values_list("pk", "child_id")
            )
            for diploma in diplomas:
                diploma.level_child_id = children.get(diploma.source_registration_id)
        event_query = batch.events.select_related("actor", "diploma").defer("diploma__pdf")
        if course_scope is not None:
            event_query = event_query.filter(Q(diploma__course_number=course_scope) | Q(diploma__isnull=True))
        events = Paginator(event_query, 50).get_page(request.GET.get("page"))
        mail_context = BatchSendConfirmationView().context(request, batch, diplomas=diplomas)
        response = render(
            request,
            "diplomas/batch.html",
            {
                "batch": batch,
                "diplomas": diplomas,
                "events": events,
                "message_form": DiplomaMessageForm(instance=batch),
                **mail_context,
                "missing_text": sum(not diploma.evaluation for diploma in diplomas),
                "batch_courses": sorted({d.course_number for d in diplomas}),
                "course_scope": course_scope,
                "can_resume_course": batch.status in ("draft", "ready", "failed")
                and batch.source_schema == connection.schema_name
                and not batch.diplomas.exclude(mail_status="pending", published_at__isnull=True).exists(),
            },
        )
        response["Cache-Control"] = "private, no-store"
        return response

    def post(self, request, pk):
        if request.POST.get("action") == "course":
            get_object_or_404(DiplomaBatch, pk=pk)
            try:
                separate_draft_courses(pk, request.POST.get("course_number"), request.user)
            except ValueError as error:
                messages.error(request, str(error))
                return redirect("backend:diploma-list")
            return redirect("backend:diploma-batch", pk=pk)
        # Open tabs using the former send button must also pass through confirmation.
        if request.POST.get("action") == "send":
            if request.POST.get("confirmation_token"):
                return BatchSendConfirmationView().post(request, pk)
            return redirect("backend:diploma-send-confirmation", pk=pk)
        with transaction.atomic():
            batch = get_object_or_404(DiplomaBatch.objects.select_for_update().defer("print_pdf"), pk=pk)
            self.perform_action(request, batch)
        response = redirect("backend:diploma-batch", pk=pk)
        if request.POST.get("action") == "download" and batch.status in ("queued", "generating", "ready"):
            response["Location"] += "?download=1"
        return response

    def perform_action(self, request, batch):
        action = request.POST.get("action")
        if action == "download" and batch.status == "ready":
            return
        if action == "message" and batch.status == "draft":
            form = DiplomaMessageForm(request.POST, instance=batch)
            if not form.is_valid():
                messages.error(request, "Complétez l’objet et le texte du mail.")
                return
            form.save()
        elif action in ("download", "send") and batch.status in ("draft", "failed"):
            complete_missing_levels(batch, request.user)
            if not batch.diplomas.exists():
                messages.error(request, "Aucun enfant dans cette préparation : choisissez un cours avec des inscrits.")
                return
            if batch.diplomas.filter(evaluation="").exists():
                messages.error(
                    request,
                    "Le texte à imprimer manque sur certains diplômes. Dans les lignes jaunes du tableau, "
                    "cliquez sur « Modifier », renseignez « Texte sur le diplôme », puis enregistrez.",
                )
                return
            batch.status = "queued"
            batch.save(update_fields=["status", "modified"])
            transaction.on_commit(lambda: queue_generation(batch, send_after=action == "send"))
        elif action == "send" and batch.status == "ready":
            transaction.on_commit(lambda: queue_mail(batch))
        else:
            messages.error(request, "Cette action n’est pas disponible dans l’état actuel.")
            return
        DiplomaEvent.objects.create(
            batch=batch, actor=request.user, action="generate" if action == "download" else action
        )
        if action == "send":
            count = batch.diplomas.filter(mail_status="pending").count()
            messages.success(
                request,
                "Envoi demandé pour %(count)s email%(plural)s. "
                "Les diplômes seront aussi disponibles sur les comptes des familles."
                % {"count": count, "plural": "" if count == 1 else "s"},
            )


def queue_mail(batch):
    try:
        send_batch.delay(str(batch.pk))
    except Exception as exc:
        DiplomaEvent.objects.create(batch=batch, action="mail_queue_failed", detail=str(exc))


class DiplomaEditView(DiplomaEnabledMixin, FullBackendMixin, View):
    def get(self, request, pk):
        diploma = get_object_or_404(
            Diploma.objects.select_related("batch").defer("pdf", "batch__print_pdf"), pk=pk, batch__status="draft"
        )
        return render(request, "diplomas/edit.html", {"form": DiplomaForm(instance=diploma), "diploma": diploma})

    def post(self, request, pk):
        with transaction.atomic():
            diploma = get_object_or_404(Diploma, pk=pk)
            batch = get_object_or_404(DiplomaBatch.objects.select_for_update(), pk=diploma.batch_id, status="draft")
            form = DiplomaForm(request.POST, instance=diploma)
            if form.is_valid():
                form.save()
                DiplomaEvent.objects.create(batch=batch, diploma=diploma, actor=request.user, action="edited")
                return redirect("backend:diploma-batch", pk=batch.pk)
        return render(request, "diplomas/edit.html", {"form": form, "diploma": diploma})


class DiplomaPreviewView(DiplomaEnabledMixin, FullBackendMixin, View):
    def get(self, request, pk):
        diploma = get_object_or_404(Diploma.objects.select_related("batch").defer("batch__print_pdf"), pk=pk)
        complete_missing_levels(diploma.batch, request.user)
        diploma.refresh_from_db()
        try:
            content = (
                diploma.pdf
                if diploma.batch.status == "ready" and diploma.pdf
                else render_diplomas(diploma.batch, [diploma])
            )
        except Exception:
            return render(request, "diplomas/preview-error.html", {"diploma": diploma}, status=503)
        response = pdf_response(content, f"apercu-diplome-{diploma.pk}.pdf")
        response["Content-Disposition"] = f'inline; filename="apercu-diplome-{diploma.pk}.pdf"'
        return response


class BatchDownloadView(DiplomaEnabledMixin, FullBackendMixin, View):
    def get(self, request, pk):
        batch = get_object_or_404(DiplomaBatch, pk=pk, status="ready")
        DiplomaEvent.objects.create(batch=batch, actor=request.user, action="print_downloaded")
        return pdf_response(batch.print_pdf, f"diplomes-{batch.issued_on.year}.pdf")


class FamilyDiplomasView(LoginRequiredMixin, View):
    def get(self, request):
        diplomas = (
            request.user.diplomas.filter(published_at__isnull=False)
            .select_related("batch")
            .defer("pdf", "batch__print_pdf", "batch__logo")
            .order_by("-batch__issued_on", "last_name", "first_name")
        )
        return render(request, "diplomas/family.html", {"diplomas": diplomas})


class DiplomaDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        queryset = Diploma.objects.filter(pdf__isnull=False)
        if not (request.user.is_active and (request.user.is_full_manager or request.user.is_staff)):
            queryset = queryset.filter(parent=request.user, published_at__isnull=False)
        diploma = get_object_or_404(queryset, pk=pk)
        DiplomaEvent.objects.create(batch=diploma.batch, diploma=diploma, actor=request.user, action="downloaded")
        return pdf_response(diploma.pdf, f"diplome-{diploma.pk}.pdf")


class BatchSendConfirmationView(DiplomaEnabledMixin, FullBackendMixin, View):
    def context(self, request, batch, diplomas=None):
        diplomas = (
            diplomas
            if diplomas is not None
            else list(
                batch.diplomas.select_related("parent")
                .defer("pdf")
                .order_by("last_name", "first_name", "course_number", "pk")
            )
        )
        supplements = list(batch.supplements.defer("content").order_by("pk"))
        pending = [diploma for diploma in diplomas if diploma.mail_status == "pending"]
        page = Paginator(pending, 1).get_page(request.GET.get("number"))
        missing_pdfs = (
            batch.status == "ready" and batch.diplomas.filter(mail_status="pending", pdf__isnull=True).exists()
        )
        missing_text = batch.status in ("draft", "failed") and any(not diploma.evaluation for diploma in diplomas)
        preferences = global_preferences_registry.manager()
        return {
            "batch": batch,
            "page": page,
            "diploma": page.object_list[0] if page.object_list else None,
            "pending": pending,
            "delivery_total": len(pending),
            "supplements": supplements,
            "mail_counts": mail_counts(diplomas),
            "course_mail_history": course_mail_history(batch.source_schema, {d.course_number for d in diplomas}),
            "missing_text": missing_text,
            "missing_pdfs": missing_pdfs,
            "can_send": bool(pending)
            and batch.status in ("draft", "failed", "ready")
            and not missing_text
            and not missing_pdfs,
            "confirmation_token": confirmation_token(batch, diplomas, supplements, request.user),
            "from_email": preferences["email__FROM_MAIL"] or settings.DEFAULT_FROM_EMAIL,
            "reply_to": preferences["email__REPLY_TO_MAIL"],
        }

    def get(self, request, pk):
        batch = get_object_or_404(DiplomaBatch.objects.defer("print_pdf", "logo"), pk=pk)
        response = render(request, "diplomas/send-confirmation.html", self.context(request, batch))
        response["Cache-Control"] = "private, no-store"
        return response

    def post(self, request, pk):
        with transaction.atomic():
            batch = get_object_or_404(DiplomaBatch.objects.select_for_update().defer("print_pdf", "logo"), pk=pk)
            context = self.context(request, batch)
            if not context["can_send"]:
                context["error"] = "Cet envoi n’est pas disponible. Vérifiez l’état de la préparation ci-dessous."
            elif request.POST.get("action") != "send" or not confirmation_matches(
                request.POST.get("confirmation_token"), context["confirmation_token"]
            ):
                context["error"] = (
                    "La préparation a changé ou la confirmation a expiré. "
                    "Vérifiez à nouveau le message et les destinataires avant de confirmer."
                )
            else:
                BatchDetailView().perform_action(request, batch)
                return redirect("backend:diploma-batch", pk=pk)
        if request.path == reverse("backend:diploma-batch", kwargs={"pk": pk}):
            messages.error(request, context["error"])
            return redirect("backend:diploma-batch", pk=pk)
        response = render(request, "diplomas/send-confirmation.html", context, status=400)
        response["Cache-Control"] = "private, no-store"
        return response


class DiplomaSupplementPreviewView(DiplomaEnabledMixin, FullBackendMixin, View):
    def get(self, request, pk, supplement_pk):
        supplement = get_object_or_404(DiplomaSupplement, pk=supplement_pk, batch_id=pk)
        content = bytes(supplement.content)
        content_type = "application/pdf" if content.startswith(b"%PDF-") else mimetypes.guess_type(supplement.name)[0]
        inline_types = {
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
            "image/bmp",
            "image/tiff",
        }
        inline = content_type in inline_types
        response = FileResponse(
            BytesIO(content),
            content_type=content_type if inline else "application/octet-stream",
            as_attachment=not inline,
            filename=supplement.name,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "sandbox; default-src 'none'"
        return response
