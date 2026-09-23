# Rappel des informations pratiques

Activer `KEPCHUP_PRACTICAL_REMINDER` pour afficher le bouton **Communication → Rappel pratique**
sur les cours sélectionnés. Activé en local et pour Montreux Ski, réservé aux responsables complets.
Le même réglage protège l'accès direct à la page.

Installation du modèle fourni par Montreux :

```sh
python sportfac/manage.py install_montreux_practical_reminder --schema NOM_PERIODE --settings=sportfac.settings.montreux_ski --dry-run
python sportfac/manage.py install_montreux_practical_reminder --schema NOM_PERIODE --settings=sportfac.settings.montreux_ski
```

La commande préserve les modèles existants. `--replace` remplace explicitement leur contenu.
Le schéma doit désigner une période existante du déploiement ciblé. Les modèles `GenericEmail`
et `dbtemplates` sont partagés entre les périodes, comme les autres mails types : cette installation
est donc nécessaire une seule fois par déploiement, et une édition s'applique à toutes ses périodes.

Modifier ensuite le sujet et le corps dans les mails types du backend. Le modèle contient les
horaires et consignes de la capture fournie : les vérifier avant envoi. Ils ne sont pas déduits
du car, dont le modèle ne possède pas de champs horaires. Les variables enfant, dossard,
groupe, lieu et car sont résolues à partir des inscriptions actuelles. Les affectations manquantes
affichent « À communiquer ». Le logo utilise `img/logo.png` du thème via une URL absolue.

L'aperçu parcourt les enfants des cours sélectionnés. L'envoi crée une archive par inscription,
avec le destinataire et le HTML exact, puis confie chaque mail à Celery. L'archive passe de brouillon
à envoyé après acceptation par le serveur mail. Redémarrer les workers après déploiement.
Une erreur d'envoi laisse l'archive en brouillon et remonte dans les logs Celery ; aucun réessai
SMTP automatique n'est effectué. Vérifier le fournisseur avant une relance en cas d'interruption.
Un nouvel envoi depuis le bouton est volontairement un nouvel envoi, même si un rappel précédent existe.
