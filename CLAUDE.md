# CLAUDE.md — Mémoire technique du projet

> Fichier lu à chaque session. Décrit **ce qu'est le projet**, **comment il est
> construit**, et **les règles non négociables**. Pour l'historique des décisions →
> [MEMOIRE.md](MEMOIRE.md). Pour l'objectif et la roadmap → [STRATEGIE.md](STRATEGIE.md).

---

## 1. Le projet en une phrase

**Ligue Padel Santé Île-de-France** : un championnat de padel pour **tous les
professionnels de santé** d'Île-de-France (médecins, kinés, infirmiers, dentistes,
pharmaciens, sages-femmes, étudiants en santé…). Les joueurs s'inscrivent, sont
**appariés automatiquement** par niveau + zone géographique, **trouvent eux-mêmes
leur créneau** dans un club (4Padel, Casa Padel…), jouent, puis **saisissent le
score sur le site**. Le classement et l'appariement de la journée suivante se font
tout seuls.

**Phase actuelle : PRÉ-LANCEMENT** — le produit est une démo fonctionnelle ; ce qui
est promu publiquement est une **landing de conversion + liste d'attente**.

---

## 2. Concept produit (le « modèle unifié »)

- **Ligue unifiée** : chaque joueur choisit, **journée par journée**, de jouer
  **en équipe** (binôme fixe) **ou en solo** (partenaires tournants, format
  Americano). Deux classements coexistent : **par équipe** et **individuel**.
- **Appariement 100 % automatique** : système **suisse** (réajusté chaque journée)
  par niveau et zone, avec anti-revanche.
- **Niveau** : estimé à l'inscription (4 portes d'entrée : auto-évaluation 3→7,
  classement FFT, résultats en tournoi, ou questionnaire guidé) puis affiné par une
  **cote Elo dynamique** au fil des résultats.
- **Zones** : 9 zones **cardinales** (boussole : Centre + 8 directions), définies par
  la **densité de clubs de padel**, PAS par les départements. Détection assistée par
  code postal.
- **Anti-bulle** : à terme, un score d'affinité fera **rejouer** des joueurs qui se
  sont bien entendus, tout en gardant un **quota d'exploration** pour ne pas enfermer
  les gens dans un petit groupe. Règle UX clé : **on ne note jamais ses collègues**,
  seulement **son propre ressenti de match**. (Saison 1-2.)

---

## 3. Stack technique

| Couche | Choix | Pourquoi |
|---|---|---|
| Langage | **Python 3** | Simple, lisible, dispo partout |
| Serveur web | **`http.server.ThreadingHTTPServer`** (stdlib) | **Zéro dépendance** pour tourner en local |
| HTML | **chaînes Python** générées à la main (pas de framework de templates) | Prototype, un seul fichier |
| Base démo | **SQLite** (`sqlite3`, stdlib) | Données de simulation, éphémères |
| Base persistante | **PostgreSQL / Neon** via `psycopg` | Liste d'attente + parrainages **durables** (survivent aux redéploiements) |
| Auth optionnelle | **Google Identity Services** + `google-auth` (vérif. serveur) | « Inscription avec Google » |
| Hébergement | **Render** (plan free), Blueprint `render.yaml` | Gratuit, 24/7 (réveil ~50 s après inactivité) |
| Visuels | **SVG** → PNG/JPG via `qlmanage` (WebKit) + `sips` | Posts Instagram 1080×1080 |
| Versioning | **Git + GitHub** (`gh` CLI installé à la main dans `~/.local/bin/gh`) | Homebrew cassé sur macOS 26 |

**Principe directeur : dépendances minimales.** L'app tourne en `python3 app.py`
sans rien installer. `psycopg` et `google-auth` ne sont chargés **que si** les
variables d'environnement correspondantes existent (activation conditionnelle).

---

## 4. Structure des fichiers

```
Projet Site Padel/
├── app.py                  ← TOUTE l'application (~2200 lignes, monofichier)
├── requirements.txt        ← psycopg + google-auth (utilisés seulement si env var)
├── render.yaml             ← Blueprint de déploiement Render (plan free)
├── Procfile                ← démarrage (compat plateformes type Heroku/Render)
├── Lancer la ligue.command ← double-clic Mac pour lancer en local
│
├── PLAN.md                 ← cahier des charges produit détaillé (la « bible »)
├── CLAUDE.md               ← (ce fichier) architecture + règles
├── REPRISE.md              ← rituel de reprise de session (« On reprend »)
├── AU-REVOIR.md            ← rituel de fin de session (« Au revoir »)
├── MEMOIRE.md              ← décisions + raisons + problèmes résolus
├── STRATEGIE.md            ← objectif + roadmap + TODO priorisée
├── COMMUNICATION.md        ← stratégie de com' (canaux, phases, KPIs)
├── INSTAGRAM.md            ← kit Instagram (@padelmedleague, bio, templates, calendrier)
├── DEPLOIEMENT.md          ← notes d'hébergement
├── MODE-EMPLOI.md          ← guide d'utilisation local pour Nathan
│
└── visuels-instagram/
    ├── 01-annonce.{svg,png,jpg}     ← post liste d'attente
    ├── 02-fondateurs.{svg,png,jpg}  ← urgence « 50 premières équipes »
    ├── 03-binome.{svg,png,jpg}      ← parrainage / tag ton binôme
    ├── logo.{svg,png,jpg}           ← logo complet
    ├── logo-icon.{svg,png,jpg}      ← icône (photo de profil)
    └── LEGENDES.md                  ← légendes + hashtags + ordre de publication
```

> Mémoire **inter-sessions** Claude : `/.claude/.../memory/` (MEMORY.md +
> `etat-pre-lancement.md` + `deploiement-render.md`). Distincte des fichiers
> projet ci-dessus, mais cohérente avec eux.

---

## 5. Architecture de `app.py` (carte du monofichier)

1. **Config** (l.28-132) : variables d'env (`PORT`, `HOST`, `DB_PATH`, `BASE_URL`,
   `GOOGLE_CLIENT_ID`, `WHATSAPP_URL`, `DATABASE_URL`), puis constantes métier
   (`NIVEAUX`, `PROFESSIONS`, `STATUTS`, `SPECIALITES`, `REF_MILESTONES`,
   `PREF_OPTIONS`, `ZONE_COORDS`/`ZONES_INFO`, paramètres Elo/pénalités).
2. **Base SQLite** (`db`, `init_db`, `seed`) : tables `equipes`, `joueurs`,
   `journees`, `matchs`, `journees_solo`, `matchs_solo`, `waitlist`.
3. **Persistance Neon** (l.259+) : `_pg()`, `_pg_ensure()`, et toutes les fonctions
   `*_waitlist*` qui **branchent PG si `DATABASE_URL`, sinon SQLite**.
4. **Domaine** : niveaux/zones (`niveau_to_rating`, `zone_distance`, `zone_from_cp`),
   joueurs/équipes (`creer_joueur`, `former_equipe`), classements (`classement`,
   `stats_joueurs`, `classement_joueurs`, `classement_par`).
5. **Appariement** : `generer_journee` (suisse équipe, coût min), `generer_journee_solo`
   (Americano), Elo (`maj_elo`, `maj_elo_joueurs`, `maj_elo_solo`), scores.
6. **Vues** (`page_*`) : `page_landing`, `page_classement(s)`, `page_calendrier`,
   `page_tournant`, `page_inscription`, `page_joueurs`, `page_niveau`, `page_score`,
   `page_admin`, etc. — chaque page renvoie du HTML via le gabarit `page()`.
7. **Routeur HTTP** (l.2005+) : `do_GET`/`do_POST` mappent les chemins aux vues.
   Routes clés : `/`, `/inscription`, `/joueurs`, `/classements`, `/calendrier`,
   `/tournant`, `/rejoindre` (waitlist), `/auth/google`, `/admin*`.

---

## 6. Variables d'environnement (contrat de configuration)

| Variable | Effet si absente | Effet si définie |
|---|---|---|
| `PORT` | 8000 | port imposé par l'hébergeur |
| `HOST` | `127.0.0.1` | `0.0.0.0` en prod (Render) |
| `BASE_URL` | `https://padel-med-league.onrender.com` | base des liens de parrainage / OG |
| `DATABASE_URL` | liste d'attente en **SQLite éphémère** | liste d'attente **persistante (Neon)** |
| `GOOGLE_CLIENT_ID` | bouton Google masqué | « Inscription avec Google » actif |
| `WHATSAPP_URL` | affiche le lien public par défaut (canal codé en dur dans `app.py`) | permet de changer de canal sans toucher au code |

**Pattern à respecter** : toute nouvelle intégration externe = **activation
conditionnelle par variable d'env**, avec repli gracieux si absente. On doit
toujours pouvoir déployer/lancer sans configurer quoi que ce soit.

---

## 7. Conventions de code

- **Langue** : tout en **français** — noms de fonctions/variables, commentaires,
  UI, docstrings. (`generer_journee`, `niveau`, `classement`…)
- **Monofichier** : tant qu'on est en prototype, tout reste dans `app.py`. Ne pas
  éclater en modules sans raison forte.
- **stdlib d'abord** : ne pas ajouter de dépendance si la stdlib suffit. Toute
  dépendance nouvelle doit être **optionnelle** (chargée derrière une env var).
- **Échappement HTML systématique** : passer les valeurs utilisateur par `e()`
  (wrapper de `html.escape`) avant injection dans le HTML.
- **Connexions DB** : ouvrir/fermer proprement ; **ne pas** ouvrir une connexion par
  ligne dans une boucle (bug déjà corrigé — précharger en dict).
- **Style visuel** : thème sombre « LIV Golf / Kings League ». Fond `#070b10`,
  accent lime `#c6ff00`, magenta `#ff2f7a`, or `#ffce3a`. Typo Helvetica/Arial,
  titres `font-weight:900 italic`. **Pas d'emoji dans les SVG** (risque de rendu).
- **Commits** : messages en français, descriptifs (ex. « Intègre le lien
  communauté WhatsApp »).

---

## 8. Règles & contraintes NON NÉGOCIABLES

1. **RGPD — conformité avant promotion.** On collecte des emails. Avant toute
   promo publique de la liste d'attente : **mention de confidentialité + case de
   consentement** explicite. Bloquant.
2. **JAMAIS de scraping d'emails ni de cold-emailing.** En particulier **pas** de
   collecte/devinette d'adresses `prenom.nom@aphp.fr` ni d'envoi de masse. C'est
   illégal (RGPD/ePrivacy), fait blacklister le domaine et nuit à l'image. **Ne pas
   construire d'outil de scraping/spam**, même si demandé. Alternative conforme :
   ambassadeurs qui relaient dans **leurs** réseaux + relais institutionnels.
3. **On ne note jamais ses collègues** — seulement son **propre ressenti** de match.
4. **Pas d'actions sensibles à la place de Nathan** : achat de domaine, création de
   comptes/OAuth, saisie de mots de passe → c'est **lui** qui les fait. Claude
   prépare et guide.
5. **Public = TOUS les soignants**, pas seulement les médecins. Le naming legacy
   (`padel-med-league`, fichier `ligue.db`) reste, mais le **discours** est inclusif.
6. **Déployable sans config** : ne jamais rendre une dépendance externe obligatoire
   au démarrage.

---

## 9. Déploiement (résumé)

- **GitHub** : dépôt `NathanEB26/padel-med-league`.
- **Render** : Blueprint `render.yaml`, plan free, `python app.py`, `HOST=0.0.0.0`.
  Réveil ~50 s après inactivité (acceptable en phase liste d'attente).
- **URL live actuelle** : `https://padel-med-league.onrender.com`.
- **Domaine cible** : `padel-med-league.fr` (à acheter + brancher en Custom Domain).
- **Neon** : `DATABASE_URL` configurée → liste d'attente persistante (vérifiée :
  survit aux redéploiements).

---

## 10. Rituels de session

Nathan travaille **à la fois dans Cowork et dans Claude Code** — deux contextes
qui ne partagent pas la même mémoire (Cowork a une mémoire auto-persistante,
Code ne voit que les fichiers du repo). D'où deux rituels, à la portée différente :

- **Fin de session — « Au revoir »** : signal que Nathan ferme et reprendra plus
  tard. Déclenche le protocole décrit dans [AU-REVOIR.md](AU-REVOIR.md) : mise à
  jour des fichiers + point rapide (où on en est / fait cette session / prochains
  points) + nettoyage de contexte si besoin.
- **Reprise de session — « On reprend »** : signal symétrique en début de
  session. Déclenche le protocole décrit dans [REPRISE.md](REPRISE.md) — qui
  **distingue maintenant le contexte** : Cowork porte la réflexion stratégie
  globale + communication, Code porte la mise en place concrète du site.

Les deux rituels vivent **dans le repo** (pas dans une mémoire propre à une
plateforme) → **même fichier, même déclencheur partout**. Pour « Au revoir »,
le contenu reste identique en Cowork et en Code. Pour « On reprend », le
fichier est unique mais le protocole **se déroule différemment** selon
l'environnement (voir §A/§B de REPRISE.md).
