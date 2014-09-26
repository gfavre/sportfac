from profiles.models import FamilyUser

parents = FamilyUser.objects.filter(finished_registration=True, 
                                    paid=False, total__gt=0)

body = """Madame, Monsieur,

En passant en revue les inscriptions aux sports scolaires facultatifs, nous constatons que nous n'avons pas encore reçu le paiement pour les inscriptions de votre/vos enfant/s.

Nous vous serions reconnaissants de bien vouloir contrôler les inscriptions que vous avez saisies, de les modifier si nécessaire et de confirmer d'ici à demain soir (10.9.13) afin que nous puissions terminer le processus d'inscription."""
