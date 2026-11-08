# Facture de location de matériel — installation Montreux hiver

Le sujet et le corps du courriel sont éditables dans l’app existante des mails types
(`GenericEmail` et `dbtemplates`). Les fichiers du dépôt servent de valeurs initiales
et de repli tant que le modèle n’est pas installé. Une édition dans le backend est
utilisée par les envois suivants, sans changement de code.

L’installation est explicite, sans écriture en base au démarrage de Django. Elle
requiert `KEPCHUP_USE_APPOINTMENTS=True`, déjà activé pour Montreux hiver.

## Installation

Depuis la racine du dépôt, dans l’environnement du déploiement Montreux hiver,
remplacer `NOM_PERIODE` par le schéma d’une période existante de cette installation:

```sh
python sportfac/manage.py install_rental_invoice_email --schema NOM_PERIODE --settings=sportfac.settings.montreux_ski --dry-run
python sportfac/manage.py install_rental_invoice_email --schema NOM_PERIODE --settings=sportfac.settings.montreux_ski
```

La simulation n’écrit ni en base ni dans le cache des modèles. L’installation crée
uniquement les éléments manquants; une relance conserve les textes personnalisés,
le format HTML/texte et les paramètres du mail type existant. Elle n’envoie aucun
courriel, ne crée aucune facture et ne modifie aucune réservation.

`mailer` et `dbtemplates` sont partagés entre les périodes d’un même déploiement:
installer une seule fois pour Montreux hiver. Le schéma explicite évite d’exécuter
la commande dans un contexte indéterminé; il ne limite pas la portée des textes à
cette seule période. Aucun autre déploiement communal n’est concerné.

Déployer aussi le code et redémarrer les workers Celery. Aucune migration nouvelle
n’est requise. Ne pas installer ces modèles dans une autre base par inadvertance.

## Modification du texte

Ouvrir `/hiver/backend/site/emails`, puis **Facture de location de matériel**.
La commande affiche aussi le lien exact du formulaire d’édition.
Le sujet et le corps sont modifiables; l’option « Mail HTML » est disponible comme
pour les autres mails types. Les variables sont documentées dans le formulaire.

Le lien `{{ site_url }}{{ bill.get_absolute_url }}` mène à la facture du parent,
avec authentification. Il ne faut pas le remplacer par le lien d’administration.
Les données `rentals` concernent uniquement la facture envoyée. Les rendez-vous de
retrait et de retour peuvent manquer: conserver les conditions du modèle initial.

## Facturation et expiration

Une nouvelle facture de location créée lors d’un rendez-vous administratif est
protégée par `do_not_expire=True`. Une facture existante est réutilisée et conserve
sa politique d’expiration. L’envoi du courriel reste facultatif, case décochée par
défaut, et est mis en file après validation de la transaction.

Les factures du parcours parent conservent l’expiration habituelle. À Montreux hiver,
le délai configuré est de 60 minutes, contrôlé toutes les 5 minutes par Celery.
La facture de location seule peut expirer sans annuler le cours déjà payé.
