# Incident : sessions bloquées sur un tenant non-production (2026-08-23)

Post-mortem écrit après coup — l'enquête elle-même a été longue et le
raisonnement facile à perdre, ce document existe pour ne pas avoir à le
refaire depuis zéro la prochaine fois qu'un symptôme similaire apparaît.
Contexte général sur le modèle tenant/période : `docs/architecture-tenants.md`.

## Le signal de départ

Un parent externe (non-admin, non identifié comme testeur) est tombé, via un
résultat Google, sur une page affichant le bandeau rouge "hors production"
et l'année scolaire 2025-2026 — alors que cette période n'était plus celle en
production. Ce bandeau n'a de sens que pour un·e admin en train de
prévisualiser volontairement une autre période ; un visiteur normal ne devrait
jamais pouvoir l'atteindre sans action explicite de sa part.

## Ce qui rendait ça difficile à comprendre

Rien dans le comportement observé ne pointait vers une cause évidente : pas
d'erreur, pas de crash, juste "la mauvaise période s'affiche, pour la mauvaise
personne". Il a fallu remonter deux couches indépendantes, chacune plausible
individuellement et invisible sans lire le code en détail :

1. **`VersionMiddleware.hostname_from_request` ne se base pas sur le vrai nom
   d'hôte de la requête** (contrairement à ce que `TenantMainMiddleware`
   suggère par son nom) — il fait confiance à `request.session["period"]`
   *indéfiniment*, y compris pour un visiteur anonyme, sans jamais revalider
   ce choix contre l'état réel. La toute première visite de quiconque épingle
   sa session sur la période qui est "en production" *à ce moment précis*.
   Si la production change ensuite (nouvelle année scolaire), rien ne
   remet à jour cette épingle pour les sessions déjà existantes.
2. **Le filet de sécurité censé couvrir ce cas ne fonctionnait pas.**
   `log_everyone_out` (appelé à chaque bascule de production) avait l'air
   correct en lisant son code — il supprime bien "toutes les sessions" via
   `django.contrib.sessions.models.Session.objects.all().delete()`. Le piège :
   ce modèle Django n'est le stockage réel des sessions que si
   `SESSION_ENGINE` pointe vers le backend DB. En production,
   `SESSION_ENGINE = "django.contrib.sessions.backends.cache"` (Redis) — donc
   cette tâche supprimait des lignes dans une table que personne ne
   consultait, sans jamais toucher aux vraies sessions actives. Aucune erreur,
   aucun warning : le code s'exécute avec succès, il agit juste sur le mauvais
   stockage.

Combinées, ces deux couches expliquent tout : une session assez ancienne pour
avoir été épinglée *avant* la dernière bascule de production restait valide
et pointait silencieusement sur l'ancienne période, indéfiniment, sans
qu'aucune action admin n'ait eu lieu côté visiteur.

**Ce qui aurait raccourci l'enquête** : vérifier en premier si le mécanisme de
nettoyage/invalidation cité dans un commentaire ou une docstring ("ceci
déconnecte tout le monde", "ceci vide le cache") utilise vraiment le même
backend que celui configuré en production — un `SESSION_ENGINE`/`CACHES` qui
diffère entre settings locaux et prod est le genre de divergence qui ne se
voit qu'en lisant les deux fichiers côte à côte, jamais en local seul.

## Le correctif (4.6.5)

- `VersionMiddleware.hostname_from_request` : seul `is_kepchup_staff` peut
  rester épinglé sur une période non-production ; tout le monde d'autre est
  toujours résolu vers la période en production courante, à chaque requête —
  auto-réparation indépendante de `log_everyone_out`.
- `log_everyone_out` : détecte maintenant le backend de session
  (`SESSION_ENGINE`) et vide effectivement le cache Redis en production
  (en épargnant les clés passées en `exceptions`, ex. l'admin qui déclenche
  l'action), au lieu de ne toucher que le modèle DB.
- Nouvelle action admin (Backend → Gérer les périodes → "Déconnecter tout le
  monde") pour rattraper les sessions déjà restées bloquées avant que ce
  correctif n'existe, sans attendre leur expiration naturelle.

## Rebond : le cache-busting CSS (4.6.6)

En déployant 4.6.5 sur Oron, un rechargement normal n'affichait pas le
nouveau style (hachures vertes) sur les cours d'un autre enfant — juste la
couleur par défaut de FullCalendar. Cause distincte mais du même ordre :
`style.css` n'a jamais eu de cache-busting (contrairement à `app.min.js`, qui
a `?v={{ VERSION }}`), donc le navigateur a continué à servir sa copie en
cache jusqu'à un rechargement forcé. Corrigé dans `templates/base.html` et
les 14 thèmes — détail dans `TECH_DEBT.md` (le vrai fix, `ManifestStaticFilesStorage`,
n'a pas été fait, jugé trop risqué à improviser en pleine gestion d'incident).

## À retenir pour la prochaine fois

- Un mécanisme de nettoyage/invalidation qui a l'air correct en lisant son
  code ne l'est pas forcément — vérifier qu'il agit sur le *vrai* backend
  configuré en production, pas sur celui qui semble le plus "évident" à lire.
- Une session (ou un cache) qui persiste plus longtemps que le cycle de vie
  qu'on lui suppose est une source de bugs difficiles à reproduire en local,
  où les sessions sont généralement toutes récentes.
- Un déploiement qui "a l'air de ne rien changer" côté visuel après un
  rechargement normal vaut la peine d'un hard-reload systématique avant de
  conclure que le déploiement a échoué — le cache navigateur est un suspect
  fréquent, pas seulement le code.
