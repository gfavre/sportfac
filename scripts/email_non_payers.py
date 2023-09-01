#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function

from django.core.mail import EmailMultiAlternatives, send_mail

from profiles.models import FamilyUser


parents = FamilyUser.objects.filter(
    profile__finished_registering=True, profile__has_paid_all=False
)

body = """Madame, Monsieur,

Il y a quelques semaines, vous avez reçu un rappel relatif au paiement encore ouvert des cours des activités scolaire 
facultatives. Nous n'avons malheureusement à ce jour pas reçu votre versement, et vous sommes reconnaissants de 
régulariser cette situation d'ici au 21 décembre prochain.


total dû: CHF %s.-

sur le compte :
IBAN: CH11 0076 7000 H542 4063 8
Adresse: 
PRIM TERRE-SAINTE 
Chemin du Chaucey 7
1296 Coppet

en précisant votre identifiant dans les communications: %s


Si votre versement s'était croisé avec ce courriel nous vous remercions de ne pas en tenir compte!

En vous remerciant d’ores et déjà de votre prompte réaction, nous vous adressons nos cordiaux messages,


Remo Aeschbach
Doyen - responsable des activités scolaires facultatives EP Coppet 
EPCoppet - Terre Sainte
Chemin du Chaucey 7
1296 Coppet
remo.aeschbach@edu-vd.ch
+4122 | 557 58 58
+4179 | 417 69 93"""


written_to = []
for parent in parents:
    if not parent.bills.filter(status="waiting", total__gt=0).exists():
        continue
    written_to.append(parent)
    total = sum([bill.total for bill in parent.bills.filter(status="waiting")])
    text_content = body % (total, parent.bills.filter(status="waiting").first().billing_identifier)
    to = "%s %s <%s>" % (parent.first_name, parent.last_name, parent.email)
    subject = "Sport scolaire facultatif - EP Coppet - rappel"
    from_email = "Activites scolaires facultatives - EP Coppet - Terre Sainte <coppet@kepchup.ch>"
    send_mail(subject, text_content, from_email, [to, "Remo Aeschbach <remo.aeschbach@edu-vd.ch>"])
    print("sent to: %s" % to)
