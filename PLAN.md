# Ligue de Padel des Médecins d'Île-de-France — Plan du projet

> Document de cadrage. Version 1 — 21/06/2026.
> Objectif : définir le produit, les écrans, la base de données et l'algorithme
> d'appariement **avant** d'écrire le code.

---

## 1. Vision en une phrase

Une plateforme web où des équipes de 2 médecins s'inscrivent, reçoivent
**automatiquement** un adversaire chaque semaine (ou tous les 15 jours) réparti
par **niveau** et **zone géographique**, organisent eux-mêmes le terrain, puis
**saisissent leur score** — le **classement** se met à jour tout seul.

Le site **ne réserve pas** les terrains : il met en relation et tient le score.

---

## 2. Décisions déjà prises

| Sujet | Choix |
|---|---|
| Livrable immédiat | Ce plan (pas de code encore) |
| Hébergement / budget | À décider plus tard |
| Inscription | Ouverte, sans vérification d'identité |
| Statut médical | Choisi dans une **liste déroulante** à l'inscription |
| Appariement | **100 % automatique** |

---

## 3. Les rôles (qui fait quoi)

- **Joueur** : s'inscrit, crée ou rejoint une équipe, consulte son prochain
  match + les coordonnées de l'adversaire, saisit/valide les scores, voit le
  classement.
- **Capitaine d'équipe** : un des 2 joueurs ; responsable de la saisie du score
  (évite les doublons).
- **Administrateur (vous)** : ouvre une saison, lance la génération des poules,
  tranche les litiges et forfaits, gère la liste des clubs. *Aucune action
  manuelle requise pour l'appariement courant — il est automatique.*

---

## 4. Concepts clés

### 4.1 Le niveau

À l'inscription, le joueur estime son niveau via **4 portes d'entrée au choix**
(il prend celle où il se repère le mieux). En interne, tout est converti vers une
**échelle commune 1 à 10**, la ligue se concentrant sur la **bande 3 à 7** (cœur
amateur).

**Porte A — Auto-évaluation directe (échelle 3-7, avec descriptions affichées) :**
| Niv. | Libellé | Repères |
|---|---|---|
| 3 | Débutant + | Fondamentaux acquis, commence à jouer des matchs |
| 4 | Intermédiaire | Jeu régulier, premières stratégies, échanges tenus |
| 5 | Intermédiaire + | Technique approfondie, premiers tournois amateurs |
| 6 | Avancé | Peu de fautes directes, bonne défense, jeu offensif |
| 7 | Avancé + | Maîtrise technique et tactique complète |

**Porte B — Classement France (FFT Padel) :** le joueur saisit son n° de
licence / classement. *Rappel : classement individuel, points glissants sur
12 mois, recalculé le 1ᵉʳ mardi du mois.* On en déduit le niveau interne via une
table de correspondance (à caler ensemble).

**Porte C — Résultats habituels en tournoi :** le joueur indique la catégorie où
il joue/perfome d'habitude (P25, P50, P100, P250, P500, P1000…). Mapping
indicatif vers l'échelle interne (ex. P25-P100 ≈ 4-5, P250-P500 ≈ 6, P1000+ ≈ 7).

**Porte D — Questionnaire guidé :** pour qui ne sait pas se situer, une liste de
cases à cocher estime le niveau, p. ex. :
- Ancienneté de pratique (< 6 mois / 6-24 mois / > 2 ans)
- Fréquence (occasionnel / 1×sem / 2×+ sem)
- Sortie de vitre / défense au mur (non / parfois / maîtrisée)
- Coups au-dessus de la tête : bandeja, víbora (aucun / bandeja / les deux)
- Participation à des tournois (jamais / P25-P100 / P250+)

Chaque réponse vaut des points ; le total est converti en niveau 3-7.

> **Important — le niveau évolue ensuite tout seul** : l'estimation de départ
> n'est qu'un point d'entrée. Voir §4.5 (cote dynamique).

### 4.2 La zone géographique
Quadrillage en **9 zones (8 directions + Centre)**, placées sur une boussole
autour de Paris. La zone est **détectée automatiquement à partir du code postal**
saisi à l'inscription (table de correspondance hors ligne, sans API), et reste
modifiable à la main. Une 2ᵉ zone acceptable est possible.

| Zone | Couvre surtout | Pôles de clubs |
|---|---|---|
| **Centre** | Paris (75) | clubs intra-muros |
| **Nord** | Val-d'Oise est (95) | Roissy, Sarcelles |
| **Nord-Est** | Seine-Saint-Denis (93) | Casa Padel, 4Padel Marville |
| **Est** | Seine-et-Marne (77) | 4Padel Vaires-Torcy |
| **Sud-Est** | Val-de-Marne (94) | Padel Horizon (Sucy) |
| **Sud** | Essonne (91) | ACE Padel Évry, Wissous, Massy |
| **Sud-Ouest** | Yvelines sud (78) | Versailles, Les Pyramides |
| **Ouest** | Hauts-de-Seine (92) | Boulogne, Nanterre |
| **Nord-Ouest** | Cergy-Pontoise (95) / Mantes (78) | |

La distance entre deux zones est calculée « à vol d'oiseau » sur la boussole ;
l'appariement privilégie la même zone, puis les zones adjacentes. *(Affinage
possible plus tard avec la géolocalisation exacte des clubs déclarés.)*

### 4.3 Profil joueur : statut, spécialité, structure
Renseignés à l'inscription **individuelle** (voir §4.6).

**Statut** (liste) : Médecin libéral · Médecin hospitalier · Interne ·
Chef de clinique · Remplaçant · Médecin retraité · Étudiant en médecine ·
Autre profession de santé.

**Spécialité** (liste) : Cardiologie · Médecine générale · Anesthésie-réanimation
· Chirurgie · Radiologie · Pédiatrie · Gynécologie · Dermatologie · Ophtalmologie
· Psychiatrie · Urgences · Médecine interne · … · Autre.

**Structure d'exercice** (champ libre, avec suggestions) : hôpital, CHU, clinique,
cabinet libéral, centre de santé… *(esprit « confrérie » : profils, stats par
spécialité/structure. N'entre pas dans l'appariement.)*

### 4.6 Inscription individuelle + formation d'équipe
Chaque joueur s'inscrit **seul** et reçoit un **pseudo** (username) unique.
Pour jouer, deux joueurs **forment une équipe** : l'un recherche l'autre par
**pseudo ou email** (annuaire des joueurs « en recherche de partenaire »), et
l'équipe est créée — niveau et cote calculés depuis les 2 profils.
*(Version finale : le partenaire recevra une invitation à accepter.)*

### 4.4 La saison
Une **saison** a une fenêtre d'inscription, une date de début, une cadence
(hebdo ou bimensuelle) et un nombre de journées. À la clôture des inscriptions,
le site génère les poules et le calendrier.

### 4.5 La cote dynamique (le niveau évolue avec les résultats)
L'estimation de départ (§4.1) sert seulement à **placer** l'équipe au début.
Ensuite, chaque équipe a une **cote** qui se met à jour après chaque match,
selon une formule de type **Elo** : battre plus fort fait monter beaucoup,
perdre contre plus faible fait baisser, l'ampleur du score module l'ajustement.

Comment cette cote rend l'appariement « évolutif » :
- **En mode suisse (retenu)** : la cote est recalculée après chaque match et
  **détermine directement l'adversaire de la journée suivante** (§5). Réactif et
  automatique.
- *(En mode poules/divisions, en réserve : la cote sert à reconstituer les
  groupes et gérer montées/descentes entre saisons.)*

---

## 5. L'appariement automatique — Système suisse *(mode retenu)*

> C'est le cœur technique. **Choix retenu : système suisse**, où l'adversaire est
> recalculé **à chaque journée** selon la cote du moment. Le plus fidèle à l'idée
> « chaque semaine, on vous donne un adversaire, et ça évolue avec vos
> résultats ». Pas de poules figées.

### Principe
À chaque nouvelle journée, le site apparie les équipes deux à deux en cherchant,
pour chaque équipe, un adversaire :
1. **de niveau proche** (cote dynamique, §4.5) ;
2. **géographiquement proche** (secteur, §4.2) ;
3. **pas déjà rencontré récemment** (anti-rematch).

### Comment l'algorithme choisit
On modélise ça comme un **appariement optimal** : pour chaque paire possible
d'équipes on calcule un « coût » =
`écart de cote` + `pénalité distance géo` + `pénalité si déjà jouées récemment`.
Le site choisit l'ensemble d'appariements qui **minimise le coût total** de la
journée (algorithme de couplage de poids minimal ; une version gloutonne suffit
pour de petits effectifs, une version exacte au-delà).

**Conséquence directe :** une bonne série de victoires fait monter votre cote →
la journée suivante vous tombez sur des équipes plus fortes. L'appariement
**s'auto-régule** sans aucune action de l'admin.

### Cas particuliers à gérer
- **Nombre impair d'équipes** → une équipe a une **journée de repos** (*bye*)
  tournante, sans pénalité ; priorité à celles qui n'en ont pas encore eu.
- **Inscription au fil de l'eau** → un atout du suisse : une équipe peut **entrer
  à tout moment**, elle est intégrée dès la journée suivante avec une cote de
  départ issue de son auto-évaluation (§4.1).
- **Anti-rematch** → on mémorise l'historique ; on n'autorise un re-match que si
  aucun autre adversaire pertinent n'est disponible.
- **Forfait / match non joué dans les délais** → règle de points (§6) + l'équipe
  fautive est repérée pour les journées suivantes.

### En réserve : Poules + Championnat (round-robin)
Mode alternatif activable si un jour vous voulez une **saison fermée à calendrier
fixe** (chaque équipe affronte toutes les autres d'une poule, montées/descentes
entre divisions). Documenté mais **non retenu** comme mode principal.

---

## 5 bis. Ligue unifiée — solo OU équipe, au choix *(modèle retenu)*

> Plutôt que deux ligues séparées, **une seule ligue**. On dissout le faux
> dilemme « solo ou équipe ».

**Principe.** Au padel, l'unité sur le terrain est toujours une **paire**. Une
journée mélange donc sans effort :
1. les **équipes fixes** (duos inscrits, paire verrouillée) ;
2. les **solos**, que le système **apparie en paires ad-hoc** (par niveau, zone,
   affinité, anti-même-partenaire).

On lance ensuite l'appariement **paire contre paire** (le coût du §5 s'applique
aux paires) : une équipe fixe peut affronter une paire de solos, et inversement.

**Choix par journée.** Avant chaque journée, le joueur déclare : *je joue avec
mon binôme* / *je joue en solo* / *je passe*. Il peut **changer à chaque
journée** (suppose des comptes connectés → Saison 1).

**Deux classements complémentaires :**
- **Individuel (Cote d'Or)** — tout le monde, à chaque match (fixe ou solo).
- **Par équipe** — uniquement les **duos fixes inscrits**. Une paire de solos
  formée pour un soir ne crée pas d'entrée au classement équipe.
- *Technique :* chaque côté d'un match porte un `team_id` (si duo inscrit) ou
  reste ad-hoc. Le classement équipe ne compte que les côtés avec `team_id`.

**Décisions actées :**
- Si **un seul membre** d'un duo se présente une journée → il joue **en solo**
  ce tour-là (l'équipe ne marque pas de point équipe cette journée).
- **Classement équipe** affiché avec **points + nb de journées jouées** (pour ne
  pas pénaliser un duo qui joue moins ; départage à la moyenne si besoin).
- Léger avantage de complicité des duos rodés sur les paires de solos :
  **assumé** (l'Elo individuel lisse, et ça fait le sel des matchs).

**Inclusivité — l'appariement par niveau répond aux 2 peurs symétriques :**
- **Débutants** : l'occasion de se mettre au padel sans matchs humiliants — on
  joue contre des gens de son niveau, ambiance bienveillante.
- **Joueurs confirmés** : fini les matchs déséquilibrés ; ils trouvent des
  partenaires/adversaires **à leur hauteur**, et des soignants avec qui ils ont
  des **affinités** (réseau). Voir §10 ter (affinité).

*Conséquence sur le prototype actuel : les deux structures séparées (matchs
équipe / matchs solo) seront **fusionnées** en une seule « match = paire vs
paire » lors de la vraie version. Non prioritaire avant le lancement.*

---

## 6. Scores et classement

### Format d'un match
Padel = **2 sets gagnants** (best-of-3). Saisie : score de chaque set
(ex. 6-3 / 4-6 / 7-5).

### Barème de points (proposition)
| Issue | Points |
|---|---|
| Victoire 2-0 | 3 |
| Victoire 2-1 | 2 |
| Défaite 1-2 | 1 |
| Défaite 0-2 | 0 |
| Forfait subi | 3 (et +1 set) |
| Forfait infligé | 0 |

**Départage en cas d'égalité** : 1) confrontation directe, 2) différence de sets,
3) différence de jeux.

### Validation d'un score (anti-litige)
1. Le **capitaine A saisit** le score.
2. Le **capitaine B confirme** ou **conteste**.
3. Sans réponse sous X jours → score **auto-validé**.
4. Si contesté → l'**admin tranche**.

---

## 7. Les écrans

### Public (sans connexion)
- **Accueil** : présentation de la ligue + bouton « S'inscrire ».
- **Classements** : par poule, mis à jour en direct.
- **Calendrier / résultats** : journées passées et à venir.

### Joueur (connecté)
- **Tableau de bord** : *mon prochain match* → adversaire, niveau, zone,
  **coordonnées pour s'organiser** (tél/email), date limite.
- **Saisir / valider un score**.
- **Mon équipe** : composition, niveau, secteur, historique.
- **Mon profil** : statut, coordonnées, niveau.

### Admin (vous)
- **Validation des équipes** (si activée plus tard).
- **Gestion des saisons / journées** : créer une saison, **lancer la génération
  de la journée** (appariement suisse) en 1 clic, publier les matchs.
- **Litiges & forfaits**.
- **Annuaire des clubs** (4Padel, Casa Padel, Padel Horizon, Padel AC Roissy…)
  affiché aux joueurs comme suggestions de lieux.

---

## 8. Modèle de données (esquisse)

- **Joueur** : pseudo (unique), nom, email, téléphone, statut, **spécialité**,
  **structure d'exercice**, niveau, zone (code postal), équipe (NULL si libre),
  rôle (joueur/admin).
- **Équipe** : nom, **2 joueurs (appariés par recherche pseudo/email)**, niveau
  d'équipe, **cote dynamique**, zone(s).
- **Saison** : nom, dates, cadence, statut.
- **Journée (Round)** : numéro, dates, statut.
- **Match** : journée, équipe A, équipe B, statut (à jouer / saisi / validé /
  litige / forfait), lieu (optionnel).
- **Score** : sets, vainqueur, qui a saisi, qui a validé.
- **HistoriqueAppariement** : qui a joué contre qui (anti-rematch §5).
- **Club** : nom, adresse, département (référence d'affichage).

---

## 9. Pile technique envisagée (à confirmer avec l'hébergement)

Recommandation orientée **simplicité + coût quasi nul au départ** :
**Next.js (React)** pour le site + **base PostgreSQL managée** + authentification
par email. Déployable plus tard en un clic (type Vercel + Neon/Supabase, offres
gratuites pour démarrer). **Décision verrouillée plus tard**, comme convenu.

---

## 10. Feuille de route proposée (par lots)

- **Lot 0 — Cadrage** *(ce document)* : valider niveaux, zones, statuts, barème.
- **Lot 1 — Socle** : comptes, profils, création d'équipes.
- **Lot 2 — Saison & appariement** : cote dynamique + génération automatique des
  journées (système suisse).
- **Lot 3 — Scores & classement** : saisie, validation, classement live.
- **Lot 4 — Confort** : annuaire clubs, notifications email « voici ton match »,
  litiges/forfaits.
- **Lot 5 — Mise en ligne** : choix hébergement, nom de domaine, lancement.

---

## 10 bis. Tables de conversion vers le niveau interne *(valeurs par défaut, à corriger)*

> Proposées comme point de départ ; **à ajuster selon votre expérience du
> terrain**. Tout converge vers l'échelle interne 1-10 (bande utile 3-7).

**Porte C — Catégorie de tournoi habituelle → niveau interne**
| Vous jouez / performez surtout en… | Niveau interne |
|---|---|
| Découverte, pas encore de tournoi | 3 |
| P25 (élimination tôt) | 3-4 |
| P25 performant / P100 | 4 |
| P100 performant / P250 | 5 |
| P250-P500 performant | 6 |
| P500-P1000 et + | 7 |

**Porte B — Repère via le classement FFT (points glissants) → niveau interne**
*(très indicatif — le classement bouge ; à recaler avec les seuils FFT du moment)*
| Ordre de grandeur de points FFT | Niveau interne |
|---|---|
| < ~100 | 3-4 |
| ~100-300 | 4-5 |
| ~300-700 | 5-6 |
| ~700-1500 | 6 |
| > ~1500 | 7 |

**Niveau d'équipe** : par défaut **moyenne des 2 joueurs** (option : tirer un peu
vers le plus fort, qui « porte » souvent la paire). À trancher.

## 10 ter. Affinité & ressenti de match *(Saison 1-2)*

Pour renforcer le réseautage **sans enfermer** les gens dans un petit groupe.

**On ne note jamais les collègues.** En fin de match, chaque joueur note
seulement **son propre ressenti** (1 tap, optionnel, privé) :
> « Tu t'es éclaté·e sur ce match ? » → 😄 Génial · 🙂 Sympa · 😐 Bof

**Usage par l'algo (jamais affiché, jamais nominatif) :**
- Match « Génial » → légère **affinité privée** entre toi et les joueurs de ce
  match → petite hausse de la probabilité de les recroiser.
- Match « Bof » → aucun effet négatif sur les gens (pas de pénalité, pas de
  blacklist) ; au plus, pas de bonus.
- Signal **directionnel** : ton ressenti ne dit rien de celui des autres.

**Affinité « déclarée » (jour 1)** : zone · métier · structure · niveau. À
**moduler** (même métier = complicité ; métiers différents = brassage) — pas
« plus c'est pareil, mieux c'est ».

**Garde-fou anti-bulle = quota d'exploration** : règle type *« ≥ 1 nouveau
visage par journée »* (≈ ⅓ exploration / ⅔ affinité), curseur réglable, plus
d'exploration pour les nouveaux inscrits.

**Intégration** : tout s'ajoute au coût d'appariement (§5) comme un **bonus
d'affinité** (préférence douce, jamais une règle rigide). Cold-start : on
démarre sur l'affinité déclarée, l'affinité apprise prend le relais avec le
volume.

## 11. Décisions — cadrage (Lot 0) bouclé ✅

| Sujet | Décision |
|---|---|
| Livrable | Plan d'abord |
| Inscription | Ouverte, sans vérification |
| Profil | Statut **+ spécialité** en listes déroulantes (§4.3) |
| Format | **Ligue unifiée** : solo OU équipe au choix par journée, paire vs paire, **2 classements** individuel + équipe (§5 bis) |
| Appariement | 100 % auto, **système suisse** par niveau/zone (§5) |
| Affinité | Ressenti de match privé (jamais noter les collègues) + **quota d'exploration** anti-bulle (§10 ter, Saison 1-2) |
| Niveau | 4 portes d'entrée + **cote dynamique Elo** (§4.1, §4.5) |
| Conversions | Valeurs par défaut, à corriger au fil de l'eau (§10 bis) |
| Cadence | **Tous les 15 jours** au départ |
| Barème de points | Proposition du §6 retenue |
| Zones | **Zones cardinales par densité de clubs** : Centre/Nord/Est/Sud/Ouest (§4.2) |
| Délais | **14 j** pour jouer · **48 h** pour saisir · **5 j** pour contester |
| Niveau d'équipe | Moyenne des 2 joueurs, **tirée vers le plus fort** |
| Notifications | **Email** au départ (SMS/WhatsApp plus tard) |

**Réglages fins reportés au développement :** valeurs exactes des tables de
conversion (§10 bis), liste définitive des spécialités, formule Elo (K, impact
du score).

**Prochaine étape : Lot 1 — Socle** (comptes, profils, création d'équipes).
