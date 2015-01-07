#!/usr/bin/python
# -*- coding: utf-8 -*-

from profiles.models import FamilyUser
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives

parents = FamilyUser.objects.filter(finished_registration=True, 
                                    paid=False, total__gt=0)

body = u"""Madame, Monsieur,

À ce jour jour et sauf erreur de notre part, nous n’avons pas reçu votre paiement pour les activités de sport scolaire facultatif de votre enfant.
Nous vous saurions gré d’effectuer votre versement:

total dû: CHF %s.-

sur le compte :
IBAN: CH77 0076 7000 C507 0682 4
Adresse: AIIP, 1201 Genève

en précisant votre identifiant dans les communications: %s

Vous pouvez également passer à notre secrétariat (avec une copie imprimée du présent mail) qui pourra encaisser directement votre finance d’inscription.
En vous remerciant d’ores et déjà de votre prompte réaction, nous vous adressons nos cordiaux messages

Remo Aeschbach
Doyen
responsable du sport scolaire facultatif
EPCoppet
Chemin du Chaucey 7
1296 Coppet
remo.aeschbach@vd.educanet2.ch
+4122 | 557 58 58
+4179 | 417 69 93"""



for parent in parents:
    text_content = body % (parent.total, parent.billing_identifier)
    to = '%s %s <%s>' % (parent.first_name, parent.last_name, parent.email)
    subject = 'Sport scolaire facultatif - EP Coppet - rappel'
    from_email = 'Remo Aeschbach <remo.aeschbach@vd.educanet2.ch>'
    send_mail(subject, text_content, from_email, [to,])
    print 'sent to: %s' % to
