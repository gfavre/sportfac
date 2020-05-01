# -*- coding: utf-8 -*-
from django.utils.timezone import now

from profiles.models import Registration
from mailer.tasks import send_mail

parents = set([reg.child.family for reg in Registration.objects.filter(course__end_date__gte=now())])
for parent in parents:
    body = u"""Chers tous, 

Les villes de Nyon et de Prangins ont pris la décision de ne pas faire recommencer les sports facultatifs cette année scolaire. Tous les cours sont donc annulés. Nous en sommes vraiment désolés. 
Nous nous réjouissons de vous revoir l’année prochaine !


Guillaume Strobino
Responsable régional
Ville de Nyon & Prangins
Toutes les informations sur : www.nyon.ch/ssf"""
    to = u'{} {} {}'.format(parent.first_name, parent.last_name, parent.email)
    print(to)
    send_mail.delay(
        subject=u'Coronavirus',
        message=body,
        from_email='Guillaume Strobino <nyon@kepchup.ch>',
        recipients=[to],
        reply_to=['ssf@nyon.ch'])

len(users)
len(parents)