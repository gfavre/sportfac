from django.core.mail import send_mail
from sportfac.context_processors import *
from profiles.models import Registration


parents = set([reg.child.family for reg in Registration.objects.all()])
for parent in parents:
    body = u"""Chers parents, 

Suite à la décision 180, 181 et du plan de protection pour la pratique du chant du DFJC voici les précautions sanitaires qui seront scrupuleusement mises en place dès le jeudi 5 novembre. Pour les cours qui sont suspendus, nous décalerons simplement les semaines une fois que la pratique sera à nouveau possible. 

- Activité nautique : Pas concerné

- Badminton : AUTORISE , si la distance de 1.5m entre les élèves est respectée les élèves dès la 9e peuvent enlever le masque. Sinon masque obligatoire.

- Capoeira : AUTORISE SANS CONTACT, uniquement de la gestuelle. si la distance de 1.5m entre les élèves est respectée les élèves dès la 9e peuvent enlever le masque. Sinon masque obligatoire.

- Comédie musicale : AUTORISE SANS CONTACT, uniquement de la gestuelle. si la distance de 1.5m entre les élèves est respectée les élèves dès la 9e peuvent enlever le masque. Sinon masque obligatoire. Le chant est possible avec masque (9e à 12e année) si 2m de distance dans des locaux aérés et vastes. 

- Echec : AUTORISE, si la distance de 1.5m entre les élèves est respectée les élèves dès la 9e peuvent enlever le masque. Sinon masque obligatoire.

- Handball : SUSPENDU pour les élèves dès la 9e année jusqu'au 30 novembre compris

- Hockey sur glace : SUSPENDU pour les élèves dès la 9e année jusqu'au 30 novembre compris

- Judo : SUSPENDU pour tous jusqu'au 30 novembre compris

- Multisport : AUTORISE , si la distance de 1.5m entre les élèves est respectée les élèves dès la 9e peuvent enlever le masque. Sinon masque obligatoire.

- Natation : SUSPENDU pour tous jusqu'au 30 novembre compris

- Tennis de table : AUTORISE , si la distance de 1.5m entre les élèves est respectée les élèves dès la 9e peuvent enlever le masque. Sinon masque obligatoire.

- Tir au pistolet : AUTORISE , si la distance de 1.5m entre les élèves est respectée les élèves dès la 9e peuvent enlever le masque. Sinon masque obligatoire.

- Unihockey : SUSPENDU pour les élèves dès la 9e année jusqu'au 30 novembre compris

- Voile : Pas concerné 

- Yoga : AUTORISE ,si la distance de 1.5m entre les élèves est respectée les élèves dès la 9e peuvent enlever le masque. Sinon masque obligatoire.


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