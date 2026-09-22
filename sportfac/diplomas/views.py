from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import connection
from django.db import transaction
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from backend.views.mixins import FullBackendMixin
from registrations.models import Registration

from .forms import BatchForm
from .forms import DiplomaForm
from .forms import DiplomaMessageForm
from .models import Diploma
from .models import DiplomaBatch
from .models import DiplomaEvent
from .services import complete_missing_levels
from .services import create_batch
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
        return render(
            request, "diplomas/batches.html", {"batches": DiplomaBatch.objects.defer("print_pdf", "logo").all()}
        )


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
            batch = create_batch(form.cleaned_data, request.user)
            return redirect("backend:diploma-batch", pk=batch.pk)
        return render(request, "diplomas/create.html", {"form": form})


def queue_generation(batch, send_after=False):
    try:
        generate_batch.delay(str(batch.pk), send_after=send_after)
    except Exception as exc:
        DiplomaBatch.objects.filter(pk=batch.pk).update(status="failed", error="Mise en file impossible : " + str(exc))
        DiplomaEvent.objects.create(batch=batch, action="queue_failed", detail=str(exc))


class BatchDetailView(DiplomaEnabledMixin, FullBackendMixin, View):
    def get(self, request, pk):
        batch = get_object_or_404(DiplomaBatch.objects.defer("print_pdf", "logo"), pk=pk)
        complete_missing_levels(batch, request.user)
        diplomas = list(batch.diplomas.defer("pdf").all())
        # Registration IDs are only meaningful inside the period that created the batch.
        if batch.source_schema == connection.schema_name and settings.KEPCHUP_REGISTRATION_LEVELS:
            children = dict(
                Registration.objects.filter(
                    pk__in=[d.source_registration_id for d in diplomas if not d.evaluation]
                ).values_list("pk", "child_id")
            )
            for diploma in diplomas:
                diploma.level_child_id = children.get(diploma.source_registration_id)
        events = Paginator(batch.events.select_related("actor", "diploma").defer("diploma__pdf"), 50).get_page(
            request.GET.get("page")
        )
        return render(
            request,
            "diplomas/batch.html",
            {
                "batch": batch,
                "diplomas": diplomas,
                "events": events,
                "supplements": batch.supplements.defer("content").all(),
                "message_form": DiplomaMessageForm(instance=batch),
            },
        )

    def post(self, request, pk):
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
            messages.success(
                request, "Envoi demandé : les diplômes seront aussi disponibles sur les comptes des familles."
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
