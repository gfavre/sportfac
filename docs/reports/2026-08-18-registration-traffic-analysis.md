# Analyse du trafic — ouverture des inscriptions ssfmontreux.ch (2026-08-18)

Analyse du journal d'accès nginx de l'ouverture des inscriptions du 18 août 2026
(`ssfmontreux_ch_access.log`, 44 180 requêtes sur la journée). Rapport interactif
publié séparément : https://claude.ai/code/artifact/edfb1e12-34d2-4aed-8b7d-a5b6d97efa59
— ce document en garde une copie locale, texte, avec le détail complet des tableaux.

## Vue d'ensemble

| Métrique | Valeur |
|---|---|
| Requêtes totales | 44 180 |
| Trafic humain "métier" (hors statique/bots/scans) | 31 478 (71.2%) |
| Assets statiques (CSS/JS/images) | 12 144 (27.5%) |
| Bots + scans (Googlebot, sondes wp-admin/.env, etc.) | 777 (1.8%) |
| Temps serveur cumulé sur le trafic métier | ~3 730s (62.2 min) |

## 1. Répartition du trafic par parcours

Chaque appel `/api/*`, `/account/`, `/client/` a été rattaché à son parcours
d'origine via le `Referer` (la page qui a déclenché l'appel), pas seulement via
son URL brute — ces endpoints sont partagés entre le wizard et le backend dans
le code (`api/urls.py`), seul le Referer permet de les distinguer dans les logs.

| Parcours | Requêtes | Part |
|---|---|---|
| Wizard / inscription (`/wizard`, `/registrations`, `/postfinance`, `/account`, `/client`, ...) | 27 136 | 86.2% |
| Activités (public, non loggué : `/`, `/activities`, `/reglement`, ...) | 3 635 | 11.5% |
| Backend (admins/gestionnaires) | 674 | 2.1% |
| Autre / non résolu | 33 | 0.1% |

Sans surprise pour un jour d'ouverture : 86% du trafic métier est le tunnel
d'inscription (wizard, y compris login/compte qui en fait partie), 11.5% la
simple consultation d'activités par des visiteurs anonymes, et à peine 2.1% le
backend admin. Le trafic statique pèse en plus 27.5% du volume brut total —
confirme qu'un cache/CDN agressif sur ces assets a plus d'effet sur la charge
globale que sur le tunnel métier lui-même.

Le tenant `/hiver` (site hiver, préfixe séparé du même code) ne représente que
1.8% du trafic métier ce jour-là — négligeable pour cette analyse, sujet à part
si besoin d'un focus dédié un autre jour.

## 2. Types d'utilisateurs et sessions

**Limite des données** : le journal ne contient qu'une seule adresse IP amont
(reverse proxy) et aucun cookie de session — impossible de distinguer deux
visiteurs différents partageant le même User-Agent au même moment. Les
"sessions" ci-dessous sont reconstruites par User-Agent + rupture d'inactivité
(6 min). Fiable pour des parcours courts et cohérents ; deux personnes très
proches dans le temps avec un navigateur très répandu (ex. "iPhone Safari
générique") peuvent être fusionnées en une seule session apparente de plusieurs
heures. **Recommandation pour la prochaine ouverture** : journaliser
`X-Forwarded-For` et un identifiant de session/requête (header custom ou
cookie applicatif) pour fiabiliser ce type d'analyse.

611 sessions reconstruites, classées ainsi :

| Type | Sessions | Requêtes totales | Ce que ça représente |
|---|---|---|---|
| wizard — reached-summary | 211 | 13 255 | A soumis au moins une inscription et est arrivé sur le récapitulatif |
| wizard — completed-payment | 34 | 10 127 | Parcours complet jusqu'au paiement/succès — le "happy path" |
| wizard — anonymous-browsing | 129 | 2 237 | Entre dans le wizard, souvent va jusqu'à la confirmation, sans repasser par le récapitulatif dans la fenêtre observée |
| wizard — authenticated-abandoned | 26 | 1 573 | Se connecte mais abandonne (ex. erreur de validation 400 sur un enfant) |
| activities-browsing-only | 119 | 665 | Consulte des fiches d'activités sans jamais entrer dans le wizard |
| admin (backend) | 20 | 15 067 | Gestionnaires — inclut des sessions d'impersonation pour inscrire au nom d'une famille |
| other | 72 | 538 | Trop courtes/ambiguës pour être classées |

Des exemplaires courts et cohérents de trois de ces types ont été transformés
en tests d'intégration Django rejouables — voir §4.

## 3. URLs les plus coûteuses en temps serveur

Classement par **temps serveur cumulé = volume × latence moyenne**, pas par
latence brute seule — c'est ce qui priorise le mieux l'effort d'optimisation :
un endpoint rapide appelé des milliers de fois peut coûter plus cher au total
qu'un endpoint lent mais rare.

### Top 20 — impact total

| Endpoint | Parcours | n | avg ms | p95 ms | max ms | total s |
|---|---|---|---|---|---|---|
| GET `/api/courses/<id>/` | wizard | 6409 | 52 | 78 | 2683 | 331.6 |
| GET `/registrations/summary/` | wizard | 1516 | 135 | 245 | 1200 | 204.0 |
| GET `/wizard/steps/user-update/` | wizard | 837 | 241 | 401 | 1637 | 202.0 |
| GET `/wizard/steps/activities/` | wizard | 1074 | 158 | 303 | 1230 | 169.9 |
| GET `/` | activities | 1247 | 133 | 196 | 1400 | 166.0 |
| GET `/wizard/steps/user-create/` | wizard | 657 | 224 | 359 | 1248 | 147.3 |
| GET `/api/dashboard/users/` | backend | 281 | 482 | 802 | 1053 | 135.6 |
| GET `/wizard/steps/children/` | wizard | 715 | 182 | 333 | 1715 | 130.2 |
| GET `/api/children/` | wizard | 2268 | 54 | 63 | 1076 | 123.3 |
| GET `/activities/courses/<id>/` | activities | 265 | 439 | 922 | 1257 | 116.2 |
| GET `/client/` | wizard | 652 | 171 | 879 | 4896 | 111.2 |
| GET `/wizard/steps/confirmation/` | wizard | 707 | 151 | 306 | 883 | 107.0 |
| POST `/wizard/steps/confirmation/` | wizard | 327 | 320 | 401 | 1624 | 104.8 |
| POST `/postfinance/` | wizard | 295 | 350 | 657 | 3812 | 103.3 |
| GET `/backend/child/` | backend | 21 | 4660 | 5146 | 5858 | 97.9 |
| GET `/wizard/steps/success/` | wizard | 344 | 248 | 397 | 1497 | 85.4 |
| GET `/account/` | wizard | 369 | 225 | 367 | 1639 | 83.2 |
| POST `/api/registrations/` | wizard | 490 | 156 | 243 | 1149 | 76.5 |
| GET `/api/activities/` | wizard | 1237 | 61 | 176 | 2801 | 75.5 |
| GET `/registrations/children/` | wizard | 416 | 162 | 335 | 593 | 67.5 |

Temps serveur cumulé par parcours : wizard 75.3%, activités 15.4%, backend
9.2% — proportionnel à leur part du volume, aucun parcours n'est
disproportionnellement inefficace *dans l'ensemble* ; les problèmes sont
concentrés sur des endpoints précis (ci-dessous), pas diffus.

### Top 15 — pire latence moyenne (n ≥ 5, indépendant du volume)

| Endpoint | Parcours | n | avg ms | p95 ms | max ms | total s |
|---|---|---|---|---|---|---|
| GET `/backend/child/` | backend | 21 | 4660 | 5146 | 5858 | 97.9 |
| POST `/postfinance/new-transaction/<id>/` | wizard | 28 | 1338 | 2722 | 4856 | 37.5 |
| GET `/backend/registrations/` | backend | 21 | 1132 | 1604 | 1698 | 23.8 |
| POST `/backend/course/<id>/update` | backend | 5 | 1017 | 1569 | 1569 | 5.1 |
| GET `/backend/course/<id>/update` | backend | 5 | 639 | 654 | 654 | 3.2 |
| GET `/backend/user/<uuid>/update` | backend | 11 | 561 | 1002 | 1002 | 6.2 |
| GET `/hiver/activities/skisnowboard/` | activities | 13 | 552 | 807 | 807 | 7.2 |
| GET `/backend/` | backend | 29 | 540 | 825 | 1435 | 15.7 |
| GET `/backend/child/<id>/update` | backend | 6 | 492 | 659 | 659 | 3.0 |
| GET `/api/dashboard/users/` | backend | 281 | 482 | 802 | 1053 | 135.6 |
| GET `/activities/courses/<id>/` | activities | 265 | 439 | 922 | 1257 | 116.2 |
| GET `/backend/course/` | backend | 28 | 391 | 602 | 614 | 10.9 |
| POST `/postfinance/` | wizard | 295 | 350 | 657 | 3812 | 103.3 |
| GET `/backend/course/<id>/` | backend | 11 | 335 | 535 | 535 | 3.7 |
| POST `/wizard/steps/user-create/` | wizard | 79 | 330 | 923 | 994 | 26.0 |

**Observation transversale** : quasiment toutes les pages `/backend/*` de ce
tableau (335-4660ms) sont nettement plus lentes que l'équivalent côté
wizard/activités (typiquement 130-350ms), y compris des pages simples avec
très peu de trafic (`n` = 5 à 29). Au-delà des deux causes déjà identifiées
sur `ChildListView` (voir §4), ça vaut la peine de vérifier s'il n'y a pas un
coût partagé au niveau du template de base backend ou d'un context processor
commun à toutes ces vues, plutôt que 6 causes indépendantes à corriger une par
une.

## 4. Priorités d'optimisation

Classées par rapport effort/impact estimé, pas seulement par latence brute.

### 1. `GET /backend/child/` — 4.7s en moyenne, sur 21 chargements, sans exception (min 4.2s, max 5.9s)

Latence plate quelle que soit l'heure de la journée (05h47 à 09h55, charge
variable) — pas un pic de concurrence, c'est structurel. Root-cause
identifiée dans le code :

- `ChildListView` (`sportfac/backend/views/user_views.py:309`) — pas de
  `paginate_by`, pas de scoping (un gestionnaire complet voit tous les
  `Child` jamais créés, toute l'historique).
- Le template (`sportfac/backend/templates/backend/user/child-list.html:139-197`)
  appelle `reverse()` jusqu'à 5× par ligne pour construire les boutons
  d'action. DataTables ne pagine que côté client ici — tout le tableau HTML
  est généré côté serveur avant tout paging.

**Fix suggéré** : ajouter `paginate_by`, filtrer par année scolaire courante,
précalculer les URLs plutôt que 5×`reverse()`/ligne. Faible volume ce jour-là
(21 appels) mais bloque un admin en pleine effervescence du matin d'ouverture.
`GET /backend/registrations/` (1.1s avg) montre le même symptôme et mérite la
même vérification.

> **Statut : corrigé le 2026-08-18**, même jour que ce rapport — bascule sur
> le même patron DataTables server-side que la liste des utilisateurs
> (`DashboardChildrenView` / `api:all_children`, voir `TECH_DEBT.md` pour le
> détail). Vérifié par requête réelle contre la base (pagination, tri,
> recherche, gating des actions), pas encore testé visuellement dans un
> navigateur — un smoke test manuel de `/backend/child/` reste recommandé
> avant de considérer le sujet définitivement clos.

### 2. `GET /api/courses/<id>/` — 331.6s de temps serveur cumulé, 6 409 appels (le plus gros poste toutes URLs confondues)

Chaque appel est rapide (52ms en moyenne) mais le SPA du wizard interroge les
cours **un par un** : les traces de session montrent un même utilisateur
déclenchant 20 à 50 requêtes individuelles en quelques minutes en scrollant
la liste d'activités (polling de disponibilité par carte de cours affichée).

**Fix suggéré** : grouper en un seul appel batché (`/api/courses/?ids=...`)
ou pousser les places disponibles via un mécanisme push plutôt qu'un polling
par carte visible. Plus gros gain total possible, car ça touche le tunnel
principal (86% du trafic).

### 3. `GET /api/dashboard/users/` — 482ms en moyenne, et rafales de 5 appels identiques en moins d'une seconde côté admin

Observé dans une session admin : 5 requêtes vers le même endpoint entre
08:54:55 et 08:54:56. Ressemble à un ré-affichage React qui redéclenche le
fetch (effet dupliqué / absence de déduplication de requête) plutôt qu'à un
vrai besoin de rafraîchir 5×.

**Fix suggéré** : dédupliquer côté client (ex. SWR/React Query avec clé
stable) avant d'optimiser la requête elle-même.

### 4. `GET /activities/courses/<id>/` — 438ms en moyenne sur une page publique et anonyme (265 appels)

Page de détail de cours, consultable sans compte, contenu qui ne change pas
à la seconde. Bonne candidate pour un cache HTTP (`cache_page` ou
équivalent) — le gain profiterait directement au 11.5% de trafic
"activités" qui n'a aucune raison d'attendre 440ms pour du contenu
quasi-statique.

### 5. `GET /backend/registrations/` — 1.1s en moyenne (21 appels)

Même famille de symptôme que #1 ; probablement un correctif rapide une fois
le patron du #1 en main. Voir aussi l'observation transversale du §3 sur
l'ensemble du backend.

## 5. Tests d'intégration créés

Fichier : `sportfac/wizard/tests/test_session_replays.py` (nouveau).

Trois sessions réelles, réduites à leur séquence de transitions d'état
significative (les appels de polling redondants — dizaines de `GET
/api/courses/<id>/` identiques — ont été condensés à un ou deux appels
représentatifs, pas rejoués tels quels), rejouées avec le client de test
Django existant (`TenantTestCase`, `UserMixin`, factories du projet) :

1. **`WizardHappyPathReplayTests`** (session "wizard-completed-payment") —
   famille authentifiée → mise à jour du profil → activités → inscription
   d'un enfant à un cours → confirmation → succès. Vérifie l'état final en
   base : `Registration.status == valid`, `Bill` rattachée à la bonne
   famille avec un total positif, `RegistrationValidation.consent_given`.
2. **`WizardImpersonationReplayTests`** (session "admin") — un gestionnaire
   démarre une impersonation, complète une inscription au nom de la
   famille, arrête l'impersonation, retrouve l'accès backend.
3. **`WizardValidationRetryReplayTests`** (session
   "wizard-authenticated-abandoned") — `POST /api/children/` sans
   `school_year` → 400, puis `PUT /api/children/<id>/` corrigé → 200.

**Statut d'exécution** : les 3 tests passent (`Ran 3 tests ... OK`), vérifié
en exécution réelle localement, pas seulement en relecture de code.

## 6. Bug d'infrastructure découvert en cours de route

En essayant de faire tourner la suite de tests localement pour valider les
tests ci-dessus, la suite `TenantTestCase` s'est révélée **cassée pour tous
les tests du dépôt**, pas seulement les nouveaux — sans rapport avec cette
analyse de trafic, mais bloquant pour quiconque veut lancer `manage.py test`
localement en ce moment :

- `sportfac/backend/signals.py:11` (`clear_tenant_cache`, câblé sur les
  signaux `post_save`/`post_delete` de `YearTenant`, donc déclenché à chaque
  création de tenant de test) appelle `cache.delete_pattern(...)` — une
  méthode propre à `django-redis`, déjà signalée comme telle par un
  commentaire existant sur cette ligne (`# ⚠️ selon backend, si Redis -> tu
  peux utiliser cache.delete_pattern`).
- `sportfac/sportfac/settings/test.py:41` configure
  `django.core.cache.backends.locmem.LocMemCache`, qui n'a pas
  `delete_pattern` → `setUpClass` lève une exception pour **tout**
  `TenantTestCase`, confirmé en lançant les tests préexistants
  `wizard/tests/test_views.py` et `test_workflow.py`.
- Nécessite aussi `DB_NAME=kepchup` en local (Postgres en peer-auth) pour
  passer l'import des settings.

**Pas encore corrigé** — deux options : basculer `CACHES["default"]` de
`settings/test.py` vers `django-redis` (si une dépendance Redis locale pour
les tests est acceptable), ou faire de `_invalidate_all_tenant_caches()`
un no-op / un `cache.clear()` de repli quand le backend configuré ne
supporte pas `delete_pattern`.

## Méthodologie

- Requêtes classées par préfixe d'URL, avec résolution via le `Referer` pour
  les appels `/api`, `/account` et `/client` ambigus (partagés entre wizard
  et backend dans le routing réel du code).
- User-Agents reconnus comme bots/crawlers exclus du calcul de sessions et
  des parts de trafic (regex sur bot/crawl/spider + libs HTTP courantes :
  curl, python-requests, go-http-client, etc.).
- Sessions reconstruites par User-Agent + rupture d'inactivité de 6 minutes
  (voir limite en §2).
- IDs numériques et UUID normalisés dans les URLs (`<id>`, `<uuid>`) avant
  agrégation des statistiques de latence, pour regrouper les vues
  paramétrées (ex. `/api/courses/67/` et `/api/courses/52/` → même ligne).
