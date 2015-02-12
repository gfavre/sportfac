recipients = ("viviane.aeby@inbox.com", "twixette75@hotmail.com", "yvanama@bluewin.ch", "judithkessi@hotmail.com", "judithkessi@hotmail.com", "patricia.klein@bluewin.ch", "dmigliorini@bluewin.ch", "esmoser@gmx.ch", "curtinniemi@gmail.com", "claire.bernier@ymail.com", "nadia.durrani@gmail.com", "nadia.durrani@gmail.com", "sandrawetherall@gmail.com", "gouin@bluewin.ch", "remo.aeschbach@vd.educanet2.ch")



from django.core.mail import send_mail

for recipient in recipients:
    body = """Madame, Monsieur,
    
Le mail précédemment envoyé "SSF - EPCoppet - test de natation | 812 - initiation au vélo" résulte d'une fausse manipulation. 

Merci de ne pas en tenir compte. Vous pouvez sans autre le supprimer.

En nous excusant de cette erreur, nous vous adressons nos meilleures salutations.


Remo Aeschbach
Doyen
responsable du sport scolaire facultatif
EPCoppet""" 
    send_mail('Erreur: SSF - EPCoppet - test de natation | 812 - initiation au vélo',
              body,
              'Remo Aeschbach <remo.aeschbach@vd.educanet2.ch>',
              [recipient,])
