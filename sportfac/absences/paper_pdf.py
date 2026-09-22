from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.http import HttpResponse
from django.shortcuts import render

from mailer.pdfutils import PDFRenderer

from .paper import attendance_data
from .paper import next_attendance_date


class AttendancePDFRenderer(PDFRenderer):
    message_template = "absences/paper-attendance-pdf.html"
    is_landscape = True


def attendance_pdf_response(request, courses):
    selected_date = None
    error = ""
    if request.GET.get("date"):
        try:
            selected_date = date.fromisoformat(request.GET["date"])
        except ValueError:
            error = "Indiquez une date au format AAAA-MM-JJ."
    entries = []
    available_dates = set()
    courses = list(courses.prefetch_related("sessions", "instructors").order_by("number", "pk"))
    for course in courses:
        available_dates.update(course.all_dates)
        day = selected_date or next_attendance_date(course)
        ready = not error and day is not None and day in course.all_dates
        entries.append({"course": course, "day": day, "ready": ready})
    ready_entries = [entry for entry in entries if entry["ready"]]
    incomplete = len(ready_entries) != len(entries)
    if error or not ready_entries or "prepare" in request.GET or (incomplete and request.GET.get("available") != "1"):
        return render(
            request,
            "absences/prepare-paper-pdf.html",
            {
                "entries": entries,
                "ready_count": len(ready_entries),
                "excluded_count": len(entries) - len(ready_entries),
                "error": error,
                "selected_date": selected_date,
                "date_value": request.GET.get("date", ""),
                "available_dates": sorted(available_dates),
            },
            status=400 if error else 200,
        )
    sheets = [attendance_data(entry["course"], entry["day"]) for entry in ready_entries]
    renderer = AttendancePDFRenderer({"sheets": sheets}, request)
    with TemporaryDirectory() as directory:
        path = Path(directory) / "liste-suivi-cours.pdf"
        renderer.render_to_pdf(str(path))
        response = HttpResponse(path.read_bytes(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="liste-suivi-cours.pdf"'
    return response
