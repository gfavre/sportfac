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

Modifier ensuite le sujet et le contenu dans les mails types du backend. Le booléen « Mail HTML »
active l’éditeur visuel ; les autres mails restent en texte simple par défaut. Les variables Django
doivent rester intactes. Leur syntaxe est validée à la sauvegarde et le HTML est filtré pour conserver
les tableaux et la mise en forme sans scripts ni événements actifs. L’aperçu HTML est isolé dans
une iframe sans scripts ni accès à la page d’administration. Le modèle contient les
horaires et consignes de la capture fournie : les vérifier avant envoi. Ils ne sont pas déduits
du car, dont le modèle ne possède pas de champs horaires. Les variables enfant, dossard,
groupe, lieu et car sont résolues à partir des inscriptions actuelles. Les affectations manquantes
affichent « À communiquer ». Le logo utilise `img/logo.png` du thème via une URL absolue.

L'aperçu parcourt les enfants des cours sélectionnés. L'envoi crée une archive par inscription,
avec le destinataire et le HTML exact, puis confie chaque mail à Celery. L'archive passe de brouillon
à envoyé après acceptation par le serveur mail. Redémarrer les workers après déploiement.
Le format HTML/texte est enregistré dans l’archive au moment de la mise en file : modifier ensuite
le mail type ne change pas les messages en attente. Les mails HTML comportent une alternative texte.
Au déploiement, installer les dépendances puis appliquer les migrations habituelles, y compris
au schéma partagé : `mailer.0009_email_html` active HTML pour les rappels existants et leurs archives.
Une erreur d'envoi laisse l'archive en brouillon et remonte dans les logs Celery ; aucun réessai
SMTP automatique n'est effectué. Vérifier le fournisseur avant une relance en cas d'interruption.
Un nouvel envoi depuis le bouton est volontairement un nouvel envoi, même si un rappel précédent existe.

L’éditeur des mails est Jodit 4.15.14 (MIT), installé via npm et servi localement, sans CDN.
Les variables `{{ … }}` restent visibles dans le texte ; celles des attributs (par exemple
`{{ logo_url }}` dans l’image) sont accessibles via « Source ». Elles ne sont résolues que dans
l’aperçu et à l’envoi. L’ancienne configuration `protectedSource` de CKEditor les masquait visuellement.
Après une mise à jour de la version épinglée dans `package.json`, exécuter
`npm run build:mail-editor` pour recopier les fichiers JS/CSS et la licence dans les assets Django,
puis `collectstatic` au déploiement. Les tests JS chargent cette distribution réelle et contrôlent
la conservation des variables du modèle Montreux.
