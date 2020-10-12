from django.core.mail import send_mail
from sportfac.context_processors import *
from profiles.models import Registration


parents = set([reg.child.family for reg in Registration.objects.all()])
for parent in parents:
    body = u"""Chers parents, 

Il reste encore passablement de places libres pour les Sports Scolaires Facultatifs !

Si les cours ci-dessous n’ont pas plus d’inscriptions d’ici au 21 octobre 2020, nous nous verrons dans l’obligation de les fermer.

- FUTSAL MARENS
- RUGBY MARENS
- TENNIS DE TABLE MARDI et VENDREDI
- TENNIS DÉBUTANT ET INTERMÉDIAIRE
- ULTIMATE FRISBEE

J’attire également votre attention sur le fait que vous pouvez déjà inscrire vos enfants pour le 2e semestre. 

En vous espérant en bonne santé, je vous adresse mes meilleures salutations, 

Guillaume Strobino
Responsable régional
Ville de Nyon & Prangins
Toutes les informations sur : www.nyon.ch/ssf"""
    
    to = u'%s %s <%s>' % (parent.first_name, parent.last_name, parent.email)
    print to
    send_mail(u'Inscriptions au sport scolaire facultatif - Nyon-Prangins',
              body,
              u'Guillaume Strobino <ssf@nyon.ch>',
              [to,])

len(parents)