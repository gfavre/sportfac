from django.core.mail import send_mail
from sportfac.context_processors import *
from profiles.models import Registration


parents = set([reg.child.family for reg in Registration.objects.all()])
for parent in parents:
    body = u"""Chers parents, 

Suite aux nouvelles mesures sanitaires édictées par le conseil d'état du canton de Vaud du vendredi 23 octobre, les élèves en âge du secondaire I (9s à 12s) doivent porter un masque constamment. Ils pourront ôter ce dernier uniquement lors de la pratique sportive. (cf. nouvelle règle scolaire). 

Les sports de contact étant toujours autorisés, nous avons néanmoins encouragé nos moniteurs à diminuer les contacts entre les élèves. 

Merci de votre compréhension

Cordialement, 

Guillaume Strobino
Responsable régional
Ville de Nyon & Prangins
Toutes les informations sur : www.nyon.ch/ssf"""
    
    to = u'%s %s <%s>' % (parent.first_name, parent.last_name, parent.email)
    print to
    send_mail(u'Sport scolaire facultatif de Nyon-Prangins - nouvelles mesures sanitaires',
              body,
              u'Guillaume Strobino <ssf@nyon.ch>',
              [to,])

len(parents)