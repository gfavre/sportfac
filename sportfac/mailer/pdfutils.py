import json
import os

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.template import loader
from django.utils.encoding import smart_str
from django.utils.translation import activate

import pypdftk
import requests
from backend.dynamic_preferences_registry import global_preferences_registry
from sekizai.context import SekizaiContext

from sportfac.context_processors import kepchup_context


global_preferences = global_preferences_registry.manager()


def get_ssf_decompte_heures(course, instructor):
    """
    pdftk sportfac/static/pdf/SSF_decompte_moniteur.pdf dump_data_fields
    """
    pdf_file = os.path.join(settings.STATIC_ROOT, "pdf", "SSF_decompte_moniteur.pdf")

    fields = {
        "Escol": global_preferences["email__SCHOOL_NAME"],
        "Discipline": course.activity.name,
        "groupe n°": course.number,
        "du": course.start_date.strftime("%d/%m/%Y"),
        "au": course.end_date.strftime("%d/%m/%Y"),
        "Nom": instructor.last_name,
        "Prénom": instructor.first_name,
        "Adresse": instructor.address,
        "NPA/Localité": f"{instructor.zipcode} {instructor.city}",
        "Naissance": instructor.birth_date and instructor.birth_date.strftime("%d/%m/%Y") or "",
        "Tel portable": instructor.best_phone and instructor.best_phone.as_national or "",
        "IBAN": instructor.iban,
        "Banque/CCP": instructor.bank_name,
        "Formation  MEP diplômé": instructor.is_mep and "On",
        "Instituteur  Maître généraliste": instructor.is_teacher and "On",
        "Moniteur JS": (not instructor.is_teacher and not instructor.is_mep) and "On",
        "Sexe  F": instructor.gender == "f" and "On",
        "H": instructor.gender == "m" and "On",
        "Nationalité": instructor.get_nationality_display(),
        "Type permis": instructor.permit_type,
        "AVS": instructor.ahv,
    }
    # noinspection PyBroadException
    try:
        return pypdftk.fill_form(pdf_path=pdf_file, datas=fields, flatten=False)
    except:  # noqa
        return pdf_file


class FakeRequest:
    pass


class PDFRenderer:
    message_template = None
    is_landscape = False

    def __init__(self, context_data, request=None):
        site = Site.objects.all()[0]
        self.fake_request = request is None
        if not request:
            request = FakeRequest()
        request.site = site
        self.request = request

        context_data["request"] = request
        context_data["STATIC_URL"] = "{}{}{}".format(
            "https://",  # self.context.get('PROTOCOL'),
            self.request.site.domain,
            settings.STATIC_URL,
        )
        context_data.update(kepchup_context(request))
        context_data.update(SekizaiContext().dicts[1])
        self.context = context_data

    @staticmethod
    def resolve_template(template):
        """Accepts a template object, path-to-template or list of paths"""
        if isinstance(template, (list, tuple)):
            return loader.select_template(template)
        if isinstance(template, str):
            return loader.get_template(template)
        return template

    def get_message_template(self):
        if self.message_template is None:
            raise ImproperlyConfigured(
                "PDFRenderer requires either a definition of "
                "'message_template' or an implementation of 'get_message_template'"
            )
        return self.resolve_template(self.message_template)

    def get_content(self, template_name):
        initial_static_url = settings.STATIC_URL
        if settings.STATIC_URL.startswith("/"):
            settings.STATIC_URL = "{}{}{}".format(
                "https://",  # self.context.get('PROTOCOL'),
                self.request.site.domain,
                settings.STATIC_URL,
            )
        if self.fake_request:
            activate(settings.LANGUAGE_CODE)
            template = self.resolve_template(template_name)
            content = smart_str(template.render(self.context))
        else:
            content = loader.render_to_string(
                template_name=self.message_template, context=self.context, request=self.request
            )
        settings.STATIC_URL = initial_static_url
        return content  # noqa: R504

    def render_to_pdf(self, output):
        """output: filelike object"""
        content = self.get_content(self.get_message_template())
        payload = json.dumps(
            {
                "backend": "chrome",
                "content": content,
                "renderType": "pdf",
                "omitBackground": False,
                "renderSettings": {
                    "emulateMedia": "print",
                    "pdfOptions": {
                        "format": "A4",
                        "landscape": self.is_landscape,
                        "preferCSSPageSize": False,
                        "omitBackground": False,
                    },
                },
                "requestSettings": {
                    "waitInterval": 0,
                    "resourceWait": 5000,
                    "resourceTimeout": 5000,
                    "doneWhen": [{"event": "domReady"}],
                },
            }
        )

        pdf = requests.post(
            f"https://PhantomJsCloud.com/api/browser/v2/{settings.PHANTOMJSCLOUD_APIKEY}/",
            payload,
        )
        f = open(output, "wb")
        f.write(pdf.content)


class CourseParticipants(PDFRenderer):
    message_template = "mailer/pdf_participants_list.html"
    is_landscape = True


class CourseParticipantsPresence(PDFRenderer):
    message_template = "mailer/pdf_participants_presence.html"

    def __init__(self, context_data):
        super().__init__(context_data)
        course = context_data["course"]
        self.context["sessions"] = list(range(0, course.number_of_sessions))


class MyCourses(PDFRenderer):
    message_template = "mailer/pdf_my_courses.html"
    is_landscape = True


class InvoiceRenderer(PDFRenderer):
    message_template = "registrations/bill-detail.html"
    is_landscape = False
