from django.template import loader
from django.core.mail import EmailMessage

from activities.models import Course
from profiles.models import FamilyUser
from backend.dynamic_preferences_registry import global_preferences_registry

course_emails = {
    283: [
        u'Daniela Gerbaldo <daniela.gerbaldo@sicpa.com>'
    ],
    281: [
        u'Edyta Bunoan <edytaforet@yahoo.com>',
        u'Nicola Jupp <timnikontour@yahoo.co.uk>',
    ],
    280: [
        u'Marion Zahnd Furrer <info@architecum.ch>'
    ],
    200: [
        u'Edineide Fernandes <giovanny@fernandes.ch>',
        u'donatella sabbatelli riganti <sabbatellidonatella@yahoo.it>',
        u'yves detrey <yves_detrey@yahoo.com>',
        u'Stefania Salvati Guerreiro <stefaniasalvati@hotmail.com>',
        u'Marta Martins <mcst02@yahoo.fr>',
        u'bannani hatem <hasnabouazzi@yahoo.fr>',
        u'Amel Lounis <amelbenouniche@yahoo.fr>',
        u'Djamilson Oliveira <italcoap.7776@gmail.com>',
        u'David Girardin <davidgirardin@gmx.ch>',
        u'Léa Granger <cofinet2002@yahoo.fr>',
        u'Yvan von Arx <yvanvonarx@yahoo.com>',
        u'Christelle Da Rosa <duartechristelle@yahoo.fr>',
    ],
    210: [
        u'Ruqi Huang.Blumenstein <ruqiblumi@hotmail.com>',
        u'Gjylan uJAGODINI <gjylan.jagodini@evam.ch>',
        u'Valerio Pappalardo <valerio_valerio@hotmail.com>',
        u'Valentina Gashi <vali-sadi@hotmail.com>',
        u'Carole Fletgen <carole.richard@chuv.ch>',
        u'alessandra troccoli <a.troccoli@libero.it>',
        u'Marta Martins <mcst02@yahoo.fr>',
        u'bannani hatem <hasnabouazzi@yahoo.fr>',
        u'Persida Pandova <persidapandova@yahoo.fr>',
        u'Frédéric Willemin <frederic.willemin@laposte.net>',
        u'Emilia De sousa <rid06@hotmail.fr>',
        u'Gérald Gysi <gerald.gysi@evam.ch>',
        u'François Jaccard <francois.jaccard@evam.ch>',
    ],

    260: [
        u'Inès TOUTOTU <mouloud1970@romandie.com>',
        u'Cveta Veselinov <cecaveselinov@yahoo.fr>',
        u'Lou Kraehenbuehl <philippe@lesorthopedistes.ch>',
        u'Chloé Voisard <pvoisard70@yahoo.fr>',
        u'SORAYA DRIDI MUNOZ <sori_dm06@hotmail.com>',
        u'D\'ANTINO MICHEL <free8nad@yahoo.com>',
        u'Safoura Haddadi <safora_haddadi@yahoo.com>',
        u'Laurent Ortuno <laurent.ortuno@lausanne.ch>',
        u'Fabrice Delley <caroravena@yahoo.com>',
        u'Pakize Palan <pakizepalan@yahoo.fr>',
        u'Sandrine VANDENDRIESSCHE <sandrinevdd@yahoo.fr>',
        u'Yiu-MIng So <symworld@hotmail.com>',
        u'Nikita SANZGIRI <nsnikita_15@yahoo.com>',
        u'Vanessa J\'efferiss-Jones <randvjj@hotmail.com>',
        u'Komal Khan <komalkhan_71@yahoo.com>',
    ],
    220: [
        u'alessandra troccoli <a.troccoli@libero.it>',
        u'Daniel Baumslag <danbaumslag@yahoo.com>',
    ],
    270: [
        u'Carole Fletgen <carole.richard@chuv.ch>',
        u'Cèline Fontaine <fontaine.celka@yahoo.fr>',
        u'Nicola Jupp <timnikontour@yahoo.co.uk>',
        u'Pakize Palan <pakizepalan@yahoo.fr>',
    ]
}
subject_template = 'mailer/course_begin_subject.txt'
message_template = 'mailer/course_begin.txt'
subj_tmpl = loader.get_template(subject_template)
msg_tmpl = loader.get_template(message_template)
signature = global_preferences_registry.manager()['email__SIGNATURE']
users = {}
for user in FamilyUser.objects.all():
    users[user.get_email_string()] = user


# tout le 250

sent = set()


for course_nb, emails in course_emails.items():
    course = Course.objects.get(number__startswith='{} -'.format(course_nb))
    for email in emails:
        try:
            user = users[email]
        except KeyError:
            print('{} - {}'.format(course_nb, email))
            continue

        registrations = course.participants.filter(course=course, child__family=user)
        for registration in registrations:
            context = {}
            context['course'] = course
            context['registration'] = registration
            context['child'] = registration.child
            context['site_url'] = 'https://ssfmontreux.ch'
            context['site_name'] = 'SSF Montreux'
            context['signature'] = signature
            body = msg_tmpl.render(context)
            subject = subj_tmpl.render(context)
            if not registration in sent:
                print(email)
                print(subject)
                raw_input(body)
                sent.add(registration)


sent = set()
# diablerets 260
course = Course.objects.get(pk=4)
registrations = course.participants.all()
from_email = global_preferences_registry.manager()['email__FROM_MAIL']

for registration in registrations:
    if registration.child.family.get_email_string() in course_emails[260]:
        print('skip')
        continue
    context = {}
    context['course'] = course
    context['registration'] = registration
    context['child'] = registration.child
    context['site_url'] = 'https://ssfmontreux.ch'
    context['site_name'] = 'SSF Montreux'
    context['signature'] = signature
    body = msg_tmpl.render(context)
    subject = subj_tmpl.render(context)
    if not registration in sent:
        email = EmailMessage(subject=subject, body=body, from_email=from_email,
                             to=[registration.child.family.get_email_string()])
        email.send()
        sent.add(registration)


sent = set()
# diablerets 270
course = Course.objects.get(pk=6)
registrations = course.participants.all()
from_email = global_preferences_registry.manager()['email__FROM_MAIL']

for registration in registrations:
    if registration.child.family.get_email_string() in course_emails[270]:
        print('skip')
        continue
    context = {}
    context['course'] = course
    context['registration'] = registration
    context['child'] = registration.child
    context['site_url'] = 'https://ssfmontreux.ch'
    context['site_name'] = 'SSF Montreux'
    context['signature'] = signature
    body = msg_tmpl.render(context)
    subject = subj_tmpl.render(context)
    if not registration in sent:
        email = EmailMessage(subject=subject, body=body, from_email=from_email,
                             to=[registration.child.family.get_email_string()])
        email.send()
        sent.add(registration)


sent = set()
# diablerets 280
course = Course.objects.get(pk=9)
registrations = course.participants.all()
from_email = global_preferences_registry.manager()['email__FROM_MAIL']

for registration in registrations:
    if registration.child.family.get_email_string() in course_emails[280]:
        print('skip')
        continue
    context = {}
    context['course'] = course
    context['registration'] = registration
    context['child'] = registration.child
    context['site_url'] = 'https://ssfmontreux.ch'
    context['site_name'] = 'SSF Montreux'
    context['signature'] = signature
    body = msg_tmpl.render(context)
    subject = subj_tmpl.render(context)
    if not registration in sent:
        email = EmailMessage(subject=subject, body=body, from_email=from_email,
                             to=[registration.child.family.get_email_string()])
        email.send()
        sent.add(registration)


sent = set()
# diablerets 281
course = Course.objects.get(pk=7)
registrations = course.participants.all()
from_email = global_preferences_registry.manager()['email__FROM_MAIL']

for registration in registrations:
    if registration.child.family.get_email_string() in course_emails[281]:
        print('skip')
        continue
    context = {}
    context['course'] = course
    context['registration'] = registration
    context['child'] = registration.child
    context['site_url'] = 'https://ssfmontreux.ch'
    context['site_name'] = 'SSF Montreux'
    context['signature'] = signature
    body = msg_tmpl.render(context)
    subject = subj_tmpl.render(context)
    if not registration in sent:
        email = EmailMessage(subject=subject, body=body, from_email=from_email,
                             to=[registration.child.family.get_email_string()])
        email.send()
        sent.add(registration)



course = Course.objects.get(number__startswith='{} -'.format('250 -'))
registrations = course.participants.filter(course=course)
for registration in registrations:
    context = {}
    context['course'] = course
    context['registration'] = registration
    context['child'] = registration.child
    context['site_url'] = 'https://ssfmontreux.ch'
    context['site_name'] = 'SSF Montreux'
    context['signature'] = signature
    body = msg_tmpl.render(context)
    subject = subj_tmpl.render(context)
    if not registration in sent:
        print(registration.child.family.get_email_string())
        print(subject)
        raw_input(body)
        sent.add(registration)
