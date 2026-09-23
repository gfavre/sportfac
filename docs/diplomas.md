# Diplômes de fin de saison

Depuis la liste des cours, sélectionner les cours puis **Gestion → Diplômes**.
Depuis une préparation, **Tous les diplômes** permet de retrouver les diplômes des différentes saisons.

1. Choisir la saison, la date, le lieu éventuel et le texte du mail. Ajouter si
   nécessaire un descriptif de niveaux en PDF (un seul document, 10 Mo max), dans ce formulaire initial.
2. Vérifier les noms et évaluations. Le niveau enregistré est copié ; son libellé
   imprimé est modifiable. Les évaluations vides bloquent la génération.
   Les brouillons dont le texte est vide reprennent automatiquement le niveau après cours
   lors de leur consultation, de l'aperçu ou avant génération, dans la période d'origine.
   Les textes déjà renseignés et les diplômes finalisés restent inchangés.
   **Aperçu** ouvre le PDF individuel dans un nouvel onglet, généré à la demande
   pour un brouillon, sans publication ni envoi.
3. **Télécharger les diplômes** prépare les PDF en arrière-plan si nécessaire,
   puis lance automatiquement le téléchargement du fichier d'impression, sans publication ni mail.
4. **Envoyer aux familles** prépare les PDF si nécessaire, les publie dans
   **Diplômes de mes enfants** et envoie le texte affiché, le diplôme individuel et le
   descriptif éventuel. Les archives restent accessibles même lorsqu'aucun enfant
   n'existe dans la période courante. Ces opérations s'exécutent avec Celery.

La page s'actualise automatiquement pendant la préparation. Le journal conserve
les générations, téléchargements, publications et envois ; aucune confirmation d'impression n'est demandée.

Le bouton d'envoi ignore les diplômes déjà envoyés, en cours d'envoi ou en échec.
Le journal permet de vérifier le destinataire, la date et l'erreur éventuelle.
Un état `sending` persistant après arrêt d'un worker nécessite une vérification
du fournisseur mail avant toute reprise manuelle. Il n'existe pas de garantie
« exactement une fois » entre SMTP et la base de données.

Le logo est `KEPCHUP_DIPLOMA_LOGO` (par défaut `img/logo.png` du thème), surchargeable
via la préférence globale `site__DIPLOMA_LOGO`. Il est copié dans la préparation
pour que les archives ne changent pas avec le thème. Pour l'impression, prévoir
un logo de résolution suffisante. Les documents fournis par le SSF sur les niveaux
ne sont pas inventés ni intégrés automatiquement : ils sont joints par l'administrateur.

Déploiement : `migrate_schemas --shared diplomas`, puis redémarrer les workers Celery.
L'option `KEPCHUP_DIPLOMAS` est activée en local et pour Montreux Ski.
