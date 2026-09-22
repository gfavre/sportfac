import uuid

from django.conf import settings
from django.db import models

from sportfac.models import TimeStampedModel


class DiplomaBatch(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    season = models.CharField(max_length=100)
    issued_on = models.DateField()
    source_schema = models.CharField(max_length=63)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    logo = models.TextField(blank=True)  # Frozen data URL, independent of future theme changes.
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(
        max_length=20,
        default="draft",
        choices=[
            ("draft", "À préparer"),
            ("queued", "En attente de génération"),
            ("generating", "Génération en cours"),
            ("ready", "PDF prêts"),
            ("failed", "Génération en échec"),
        ],
    )
    error = models.TextField(blank=True)
    print_pdf = models.BinaryField(null=True, editable=False)

    class Meta:
        ordering = ("-created",)


class Diploma(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(DiplomaBatch, related_name="diplomas", on_delete=models.PROTECT)
    parent = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="diplomas", on_delete=models.PROTECT)
    # No FK to tenant data: certificates survive the loss of a child/course/period.
    source_registration_id = models.PositiveIntegerField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    activity = models.CharField(max_length=255)
    course_number = models.CharField(max_length=100)
    level = models.CharField(max_length=100, blank=True)
    evaluation = models.CharField(max_length=255)
    place = models.CharField(max_length=255)
    instructors = models.CharField(max_length=500)
    pdf = models.BinaryField(null=True, editable=False)
    published_at = models.DateTimeField(null=True, blank=True)
    mail_status = models.CharField(
        max_length=20,
        default="pending",
        choices=[
            ("pending", "Non envoyé"),
            ("sending", "Envoi en cours / à vérifier"),
            ("sent", "Envoyé"),
            ("failed", "Échec — à vérifier"),
        ],
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    recipient = models.EmailField(blank=True)

    class Meta:
        ordering = ("last_name", "first_name", "course_number")
        constraints = [
            models.UniqueConstraint(fields=("batch", "source_registration_id"), name="diploma_batch_registration")
        ]


class DiplomaSupplement(TimeStampedModel):
    batch = models.ForeignKey(DiplomaBatch, related_name="supplements", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    content = models.BinaryField(editable=False)


class DiplomaEvent(TimeStampedModel):
    batch = models.ForeignKey(DiplomaBatch, related_name="events", on_delete=models.PROTECT)
    diploma = models.ForeignKey(Diploma, related_name="events", on_delete=models.PROTECT, null=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(
        max_length=40,
        choices=[
            ("created", "Préparation créée"),
            ("edited", "Diplôme corrigé"),
            ("message", "Texte du mail modifié"),
            ("supplement", "Pièce jointe ajoutée"),
            ("generate", "Génération demandée"),
            ("generation_started", "Génération démarrée"),
            ("generated", "PDF archivé"),
            ("generation_completed", "Génération terminée"),
            ("generation_failed", "Échec de génération"),
            ("queue_failed", "Échec de mise en file"),
            ("publish", "Publication sur les comptes"),
            ("send", "Envoi demandé"),
            ("mail_started", "Envoi démarré"),
            ("mail_sent", "Mail accepté par le serveur"),
            ("mail_failed", "Échec d’envoi"),
            ("mail_queue_failed", "Échec de mise en file du mail"),
            ("printed", "Impression confirmée"),
            ("print_downloaded", "PDF d’impression téléchargé"),
            ("downloaded", "Diplôme téléchargé"),
        ],
    )
    detail = models.TextField(blank=True)

    class Meta:
        ordering = ("-created", "-pk")
