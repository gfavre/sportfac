from __future__ import absolute_import, print_function

from django.core.mail import send_mail
from django.urls import reverse

from profiles.models import FamilyUser, Registration

from sportfac.context_processors import *


parents = set([reg.child.family for reg in Registration.objects.filter(validated=False)])
for parent in parents:
    url = "http://www.kepchup.ch" + reverse("wizard_confirm")
    body = (
        """Madame, Monsieur,
En passant en revue les inscriptions aux sports scolaires facultatifs, nous constatons que les inscriptions pour votre/vos enfant/s ne sont 
à ce jour pas encore confirmées (passage à l'étape du paiement).
Nous vous serions reconnaissants de bien vouloir contrôler les inscriptions que vous avez saisies, de les modifier si nécessaire et de confi
rmer d'ici à demain soir (11.9.13) afin que nous puissions terminer le processus d'inscription.
Le site des inscriptions: %s
Enfin, nous vous saurions gré de verser le montant relatif à ces inscriptions sur le compte indiqué.
En vous remerciant de votre collaboration, nous vous adressons nos cordiaux messages.
Remo Aeschbach
Doyen
responsable du sport scolaire facultatif
EPCoppet
Chemin du Chaucey 7
1296 Coppet
remo.aeschbach@vd.educanet2.ch
+4122 | 557 58 58
+4179 | 417 69 93
"""
        % url
    )

    to = "%s %s <%s>" % (parent.first_name, parent.last_name, parent.email)
    print(to)
    send_mail(
        "Inscription au sport scolaire facultatif - EP Coppet",
        body,
        "Remo Aeschbach <remo.aeschbach@vd.educanet2.ch>",
        [
            to,
        ],
    )
len(users)
len(parents)
