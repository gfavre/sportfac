# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME

from mailer.pdfutils import PDFRenderer


class AbsencePDFRenderer(PDFRenderer):
    message_template = 'backend/course/absences.html'
    rasterizer = settings.PHANTOMJS_RASTERIZE_PORTRAIT


class AbsencesPDFRenderer(PDFRenderer):
    message_template = 'backend/course/multiple-absences.html'
    rasterizer = settings.PHANTOMJS_RASTERIZE_PORTRAIT


def manager_required(fct=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_manager or u.is_superuser,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if fct:
        return actual_decorator(fct)
    return actual_decorator
