from django.core.mail import EmailMessage
from django.template import loader

from activities.models import Course
from backend.dynamic_preferences_registry import global_preferences_registry
from profiles.models import FamilyUser


course_emails = {
    283: ["Daniela Gerbaldo <daniela.gerbaldo@sicpa.com>"],
    281: [
        "Edyta Bunoan <edytaforet@yahoo.com>",
        "Nicola Jupp <timnikontour@yahoo.co.uk>",
    ],
    280: ["Marion Zahnd Furrer <info@architecum.ch>"],
    200: [
        "Edineide Fernandes <giovanny@fernandes.ch>",
        "donatella sabbatelli riganti <sabbatellidonatella@yahoo.it>",
        "yves detrey <yves_detrey@yahoo.com>",
        "Stefania Salvati Guerreiro <stefaniasalvati@hotmail.com>",
        "Marta Martins <mcst02@yahoo.fr>",
        "bannani hatem <hasnabouazzi@yahoo.fr>",
        "Amel Lounis <amelbenouniche@yahoo.fr>",
        "Djamilson Oliveira <italcoap.7776@gmail.com>",
        "David Girardin <davidgirardin@gmx.ch>",
        "Léa Granger <cofinet2002@yahoo.fr>",
        "Yvan von Arx <yvanvonarx@yahoo.com>",
        "Christelle Da Rosa <duartechristelle@yahoo.fr>",
    ],
    210: [
        "Ruqi Huang.Blumenstein <ruqiblumi@hotmail.com>",
        "Gjylan uJAGODINI <gjylan.jagodini@evam.ch>",
        "Valerio Pappalardo <valerio_valerio@hotmail.com>",
        "Valentina Gashi <vali-sadi@hotmail.com>",
        "Carole Fletgen <carole.richard@chuv.ch>",
        "alessandra troccoli <a.troccoli@libero.it>",
        "Marta Martins <mcst02@yahoo.fr>",
        "bannani hatem <hasnabouazzi@yahoo.fr>",
        "Persida Pandova <persidapandova@yahoo.fr>",
        "Frédéric Willemin <frederic.willemin@laposte.net>",
        "Emilia De sousa <rid06@hotmail.fr>",
        "Gérald Gysi <gerald.gysi@evam.ch>",
        "François Jaccard <francois.jaccard@evam.ch>",
    ],
    260: [
        "Inès TOUTOTU <mouloud1970@romandie.com>",
        "Cveta Veselinov <cecaveselinov@yahoo.fr>",
        "Lou Kraehenbuehl <philippe@lesorthopedistes.ch>",
        "Chloé Voisard <pvoisard70@yahoo.fr>",
        "SORAYA DRIDI MUNOZ <sori_dm06@hotmail.com>",
        "D'ANTINO MICHEL <free8nad@yahoo.com>",
        "Safoura Haddadi <safora_haddadi@yahoo.com>",
        "Laurent Ortuno <laurent.ortuno@lausanne.ch>",
        "Fabrice Delley <caroravena@yahoo.com>",
        "Pakize Palan <pakizepalan@yahoo.fr>",
        "Sandrine VANDENDRIESSCHE <sandrinevdd@yahoo.fr>",
        "Yiu-MIng So <symworld@hotmail.com>",
        "Nikita SANZGIRI <nsnikita_15@yahoo.com>",
        "Vanessa J'efferiss-Jones <randvjj@hotmail.com>",
        "Komal Khan <komalkhan_71@yahoo.com>",
    ],
    220: [
        "alessandra troccoli <a.troccoli@libero.it>",
        "Daniel Baumslag <danbaumslag@yahoo.com>",
    ],
    270: [
        "Carole Fletgen <carole.richard@chuv.ch>",
        "Cèline Fontaine <fontaine.celka@yahoo.fr>",
        "Nicola Jupp <timnikontour@yahoo.co.uk>",
        "Pakize Palan <pakizepalan@yahoo.fr>",
    ],
}
subject_template = "mailer/course_begin_subject.txt"
message_template = "mailer/course_begin.txt"
subj_tmpl = loader.get_template(subject_template)
msg_tmpl = loader.get_template(message_template)
signature = global_preferences_registry.manager()["email__SIGNATURE"]
users = {}
for user in FamilyUser.objects.all():
    users[user.get_email_string()] = user


# tout le 250

sent = set()


for course_nb, emails in course_emails.items():
    course = Course.objects.get(number__startswith=f"{course_nb} -")
    for email in emails:
        try:
            user = users[email]
        except KeyError:
            print(f"{course_nb} - {email}")
            continue

        registrations = course.participants.filter(course=course, child__family=user)
        for registration in registrations:
            context = {}
            context["course"] = course
            context["registration"] = registration
            context["child"] = registration.child
            context["site_url"] = "https://ssfmontreux.ch"
            context["site_name"] = "SSF Montreux"
            context["signature"] = signature
            body = msg_tmpl.render(context)
            subject = subj_tmpl.render(context)
            if not registration in sent:
                print(email)
                print(subject)
                input(body)
                sent.add(registration)


sent = set()
# diablerets 260
course = Course.objects.get(pk=4)
registrations = course.participants.all()
from_email = global_preferences_registry.manager()["email__FROM_MAIL"]

for registration in registrations:
    if registration.child.family.get_email_string() in course_emails[260]:
        print("skip")
        continue
    context = {}
    context["course"] = course
    context["registration"] = registration
    context["child"] = registration.child
    context["site_url"] = "https://ssfmontreux.ch"
    context["site_name"] = "SSF Montreux"
    context["signature"] = signature
    body = msg_tmpl.render(context)
    subject = subj_tmpl.render(context)
    if not registration in sent:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[registration.child.family.get_email_string()],
        )
        email.send()
        sent.add(registration)


sent = set()
# diablerets 270
course = Course.objects.get(pk=6)
registrations = course.participants.all()
from_email = global_preferences_registry.manager()["email__FROM_MAIL"]

for registration in registrations:
    if registration.child.family.get_email_string() in course_emails[270]:
        print("skip")
        continue
    context = {}
    context["course"] = course
    context["registration"] = registration
    context["child"] = registration.child
    context["site_url"] = "https://ssfmontreux.ch"
    context["site_name"] = "SSF Montreux"
    context["signature"] = signature
    body = msg_tmpl.render(context)
    subject = subj_tmpl.render(context)
    if not registration in sent:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[registration.child.family.get_email_string()],
        )
        email.send()
        sent.add(registration)


sent = set()
# diablerets 280
course = Course.objects.get(pk=9)
registrations = course.participants.all()
from_email = global_preferences_registry.manager()["email__FROM_MAIL"]

for registration in registrations:
    if registration.child.family.get_email_string() in course_emails[280]:
        print("skip")
        continue
    context = {}
    context["course"] = course
    context["registration"] = registration
    context["child"] = registration.child
    context["site_url"] = "https://ssfmontreux.ch"
    context["site_name"] = "SSF Montreux"
    context["signature"] = signature
    body = msg_tmpl.render(context)
    subject = subj_tmpl.render(context)
    if not registration in sent:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[registration.child.family.get_email_string()],
        )
        email.send()
        sent.add(registration)


sent = set()
# diablerets 281
course = Course.objects.get(pk=7)
registrations = course.participants.all()
from_email = global_preferences_registry.manager()["email__FROM_MAIL"]

for registration in registrations:
    if registration.child.family.get_email_string() in course_emails[281]:
        print("skip")
        continue
    context = {}
    context["course"] = course
    context["registration"] = registration
    context["child"] = registration.child
    context["site_url"] = "https://ssfmontreux.ch"
    context["site_name"] = "SSF Montreux"
    context["signature"] = signature
    body = msg_tmpl.render(context)
    subject = subj_tmpl.render(context)
    if not registration in sent:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[registration.child.family.get_email_string()],
        )
        email.send()
        sent.add(registration)


course = Course.objects.get(number__startswith="{} -".format("250 -"))
registrations = course.participants.filter(course=course)
for registration in registrations:
    context = {}
    context["course"] = course
    context["registration"] = registration
    context["child"] = registration.child
    context["site_url"] = "https://ssfmontreux.ch"
    context["site_name"] = "SSF Montreux"
    context["signature"] = signature
    body = msg_tmpl.render(context)
    subject = subj_tmpl.render(context)
    if not registration in sent:
        print(registration.child.family.get_email_string())
        print(subject)
        input(body)
        sent.add(registration)


from backend.dynamic_preferences_registry import global_preferences_registry
from mailer.tasks import send_mail
from profiles.tasks import FamilyUser
from registrations.tasks import send_confirmation


subject = "Correctif - Vos inscriptions au sport scolaire facultatif"
body = """
ERRATUM - Ce mail annule le précédent qui était vide par erreur.
Madame, Monsieur,

Nous avons bien reçu vos inscriptions pour les cours suivants:

"""

global_preferences = global_preferences_registry.manager()

for user in FamilyUser.objects.exclude(validations__isnull=True):
    if not user.has_registrations:
        continue
    registration_lines = []
    for invoice in user.bills.all():
        for registration in invoice.registrations.all():
            registration_lines.append(f"• {registration.child.full_name} - {registration.course.short_name}")
    if not registration_lines:
        continue
    mail_body = (
        body + "\n".join(registration_lines) + "\n\nMerci de votre confiance.\n\nCordialement,\nL'équipe SSF Montreux"
    )
    print(f"Sending email to {user.get_email_string()}")
    send_mail.delay(
        subject=subject,
        message=mail_body,
        from_email=global_preferences["email__FROM_MAIL"],
        recipients=[user.get_email_string()],
        reply_to=[global_preferences["email__REPLY_TO_MAIL"]],
    )
