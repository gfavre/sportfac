# Reprendre les niveaux d'une période précédente

Depuis la racine du dépôt, avec l'environnement et les settings du déploiement concerné:

```sh
python sportfac/manage.py copy_child_levels
```

La commande demande la période source puis la destination. Seules les périodes prêtes
sont proposées; la destination doit commencer après la source. Saisir `q` pour annuler.

Pour choisir directement les schémas et simuler la copie:

```sh
python sportfac/manage.py copy_child_levels --source hiver2025 --destination hiver2026 --dry-run
```

Retirer `--dry-run` pour appliquer. Les arguments attendent les noms de schémas affichés
dans le menu, pas les identifiants numériques des périodes. Un argument manquant est
demandé interactivement.

Chaque `ChildActivityLevel.after_level` non vide est copié dans le `before_level`
correspondant. Les enfants sont associés exclusivement par `Child.id_lagapeo`, les
activités par leur nom exact. Les identifiants internes peuvent différer entre périodes.
Un enfant sans identifiant Lagapeo ou absent de la destination, ou une activité renommée
ou absente, est compté dans `unmatched` et ignoré. Aucun enfant ni activité n'est créé.

Un niveau destination manquant est créé. Un `before_level` déjà rempli est conservé,
sauf avec `--overwrite`. Les `after_level` et notes de destination restent inchangés,
comme toutes les données source. Les niveaux annoncés dans les réponses d'inscription
ne sont pas concernés. La répétition du transfert avec les mêmes valeurs ne modifie rien.

Le bilan indique les lignes créées (`created`), mises à jour (`updated`), conservées
(`preserved`), sans correspondance (`unmatched`) ou ambiguës (`ambiguous`). En simulation,
ces nombres représentent les opérations prévues. Toutes les écritures sont effectuées
dans une transaction sur la destination.
