# STRATEGIE.md — Cap, roadmap & TODO

> Où on va, dans quel ordre, et quoi faire **maintenant**. Mise à jour à chaque
> avancée. Le « pourquoi » des choix → [MEMOIRE.md](MEMOIRE.md). L'archi → [CLAUDE.md](CLAUDE.md).
>
> **Date de référence : 23/06/2026 — Phase : PRÉ-LANCEMENT (liste d'attente).**
>
> 📌 **Règle de travail** : tout choix stratégique tranché est consigné ici (section
> « Décisions stratégiques »), au fil de l'eau.

---

## 0. Décisions stratégiques (journal)

### S1 — Hébergement & domaine découplés : Render (hébergement) + OVH (domaine) — *23/06/2026*
**Décision** : garder le **site sur Render** et acheter **le domaine `padel-med-league.fr`
chez OVH** (registrar). Les deux sont indépendants ; on branche le domaine OVH sur
Render via 2 enregistrements DNS.
**Pourquoi** : le site est un **process Python permanent** (`http.server`), pas un site
statique. L'hébergement mutualisé OVH (PHP) ne convient pas ; un VPS OVH conviendrait
mais imposerait toute l'administration système (SSL, mises à jour, redéploiements) —
trop lourd vu le profil de Nathan. Render est **managé** (déploiement auto GitHub,
HTTPS auto, zéro maintenance) et déjà en place. L'économie d'un VPS (~1-2 €/mo) ne
vaut pas le temps perdu.
**Coûts** :
- Domaine `.fr` chez OVH : **~7-9 €/an**.
- Render **gratuit (0 €)** pendant la phase liste d'attente (réveil ~50 s toléré).
- Render **Starter ~7 $/mo (~6,5 €)** au **vrai lancement** (supprime la mise en veille).
- → Coût total en pré-lancement : **~8 €/an** (juste le domaine).
**Alternatives écartées** : OVH mutualisé (incompatible Python permanent), OVH VPS
(trop d'admin), tout-en-un OVH. Registrar alternatif noté : Cloudflare (~8 €/an).

### S2 — Modèle « open match » : appariement déclenché par les joueurs — *23/06/2026* ✅ validé
**Décision** : le mécanisme **principal** de mise en relation n'est plus « le système
t'impose un adversaire » (push) mais **« un joueur ouvre un match, le système sollicite
les compatibles »** (pull). Un joueur pose un créneau (date + club + heure), seul ou en
bloquant le slot de son binôme ; les joueurs compatibles (niveau + zone + anti-revanche
+ affinité) sont **notifiés** ; **fenêtre d'élargissement progressif** de la
compatibilité si le match ne se remplit pas (±0,5→±1 niveau, zones adjacentes). On
rejoint en 1 clic : **solo** (1 siège) ou **en duo** (2 sièges).
**Pourquoi** : résout la friction n°1 = **la coordination** (4 personnes, même créneau,
même club). L'Elo / les zones / les niveaux restent le moteur de compatibilité ; seul le
**déclencheur** change. Modèle éprouvé (« open match » type Playtomic).
**Implication** : nécessite un système de **notifications** (email d'abord, push ensuite
via PWA). Spéc détaillée à écrire dans PLAN.md au moment de l'implémentation.

### S3 — Compte à rebours jusqu'au 1er septembre 2026 — *23/06/2026* ✅ validé
**Décision** : countdown stylisé (néon LIV/Kings) en héros de la landing, jusqu'au
**1er septembre 2026** (date ferme = coup d'envoi Saison 1). Renforce le CTA liste
d'attente. Script JS, zéro dépendance.

### S4 — Profil joueur : côté préféré + tolérance — *23/06/2026* ✅ validé
**Décision** : ajouter au profil **côté préféré** (Gauche / Droite / Indifférent) +
**tolérance à jouer de l'autre côté** sur une **échelle 0-10**. Alimente la qualité
d'appariement (paires gaucher/droitier, ou flexibilité si tolérance haute).

### S5 — Google login déprioritisé — *23/06/2026* ✅ validé
**Décision** : en pré-inscription, **email seul** (un champ de moins = meilleure
conversion). Le code Google reste en place, réactivable plus tard via `GOOGLE_CLIENT_ID`.
Sort des actions actives → backlog.

### S6 — Mobile : responsive maintenant → PWA → natif iOS plus tard — *23/06/2026* ✅ validé
**Décision** : **(a)** site **responsive** impeccable = priorité immédiate (trafic =
Instagram = mobile). **(b)** « l'app » = **PWA** (installable écran d'accueil, push,
iOS+Android, réutilise le code web, coût quasi nul). **(c)** app **native iOS** repoussée
en phase Croissance (compte dev Apple 99 $/an + App Store + maintenance = prématuré).

### S8 — Matchs amicaux + cote fantôme (shadow rating) — *23/06/2026* ✅ validé, en backlog
**Décision** : garder **1 match officiel / 15 jours** pour tout le monde (cadence qui
préserve l'équité du classement), mais permettre des **matchs amicaux** en plus. **Gate
clé** : on ne peut **ouvrir ou rejoindre un amical que si on a honoré son officiel** de
la période → l'amical devient une **récompense d'engagement** et pousse à honorer
l'officiel (qui fait vivre la ligue). Gate basé sur « avoir **honoré** son officiel »
(pas « gagné »), pour ne pas punir un joueur que le système n'a pas su apparier.
**Traitement des amicaux (validé)** :
- **Hors classement officiel / hors Elo public** (préserve l'équité de la cadence 15j).
- **Comptabilisés « pour le fun » dans les stats perso** : bilans tête-à-tête (« X
  victoires / Y défaites contre tel adversaire »), historique, etc.
- **Cote fantôme privée (shadow rating)** : une cote qui **inclut les amicaux**,
  **compilée mais NON publique**.
- **Analyse différée** : au bout de plusieurs mois, comparer cote publique (officiels
  seuls) vs cote fantôme (tout) → comprendre **le pourquoi/comment des discordances**
  (sous-cotation, échantillon officiel trop petit, sandbagging, etc.). Outil de
  **qualité d'appariement**, pas de classement.
**Dépendance** : s'appuie sur le **modèle open match (S2)** → à implémenter après lui.
**Statut** : backlog produit, **non prioritaire** (mode de travail asynchrone).

### S10 — Stratégie d'événements physiques (IRL) — *24/06/2026* 🟡 brainstorm validé, en backlog
**Décision** : programmer des temps forts « en vrai » tout au long de l'année — ils
convertissent la liste d'attente, nourrissent l'Instagram et fidélisent. Programme :
- **Soirée de lancement** (sept) dans un club partenaire : initiation + 1ers matchs + verre.
- **After-works padel mensuels** par zone (récurrent, convivial, réseau + jeu).
- **Tournois « open » trimestriels** (Americano géant, tous niveaux).
- **Battles inter-groupes** (Cardio vs Anesthésie, inter-hôpitaux, inter-facs) → lien S9.
- **Journée des Fondateurs** (50 premières équipes), **initiations débutants**,
  **Masters de fin de saison** (« Kings League »), **tournoi caritatif** (cause santé).
**Angles** : convivialité, réseau, découverte, esprit de corps. **Statut** : backlog
non prioritaire ; seule la **soirée de lancement** se rapproche de l'échéance sept 2026.

### S11 — Stratégie de communication & viralité — *24/06/2026* 🟡 brainstorm validé
**3 moteurs de croissance** : (1) **relais institutionnels** (levier n°1 au démarrage),
(2) **viralité par les inscrits** (boule de neige), (3) **contenu Instagram** (preuve
sociale). 
**Relais** : liste complète des syndicats/ordres/URPS/fédés étudiantes/assos d'IDF par
profession → `CONTACTS-RELAIS.md`. **SIHP = accord obtenu** (mailing list) → mail clé en
main dans `KIT-AMBASSADEUR.md` §2bis. Priorité : (a) ceux qui ont dit oui, (b) cibles
jeunes/virales (corpos, internes, FNEK/FNESI), (c) CGOS & assos sportives.
**Viralité (optimiser le coefficient K)** : le **binôme est l'unité virale** (inviter
son partenaire est intrinsèque au padel) ; partage juste après l'inscription ; rareté du
Club des Fondateurs ; à ajouter → étape « invite ton binôme », classement des
ambassadeurs, carte perso partageable, boucle événementielle (S10).
**Mesure** : ✅ **suivi de source** implémenté (`?from=<source>`, ex. `?from=sihp`) —
stocké en base et visible dans l'admin → on saura quel relais convertit.

### S7 — Emails : provider transactionnel + authentification DNS — *23/06/2026* ✅ validé (à mettre en place après le domaine)
**Décision** : envoi de mails automatiques via un **provider transactionnel** (reco
**Brevo** — français, RGPD-friendly, gratuit 300 mails/j ; alternatives Resend/Mailgun),
appelé en **API HTTP depuis `app.py`** (stdlib `urllib`, **zéro nouvelle dépendance**),
**activé conditionnellement** par env var (`EMAIL_API_KEY`). **Authentification DNS
obligatoire** sur le domaine : **SPF + DKIM + DMARC** (sinon spam / usurpation possible).
Réception : **alias gratuit OVH** `contact@padel-med-league.fr` → redirigé vers le Gmail.
**Usages** : confirmation d'inscription, paliers de parrainage, **notifications open
match (S2)**, rappels créneau/score/résultats. **Garde-fou** : mails **transactionnels
consentis uniquement** — jamais de cold-emailing/scraping (voir CLAUDE.md règle 2).
**Séquence** : domaine → compte Brevo (par Nathan) → DNS SPF/DKIM/DMARC → câblage du code.

### S9 — Statistiques : ce qu'on met en avant — *23/06/2026* ✅ validé, en backlog
**Décision** : framework stats à 5 niveaux (construit sur l'existant `stats_joueurs`,
`classement_joueurs`, `classement_par`).
- **A — Tableau de bord perso** : héros = **cote + courbe d'évolution** + **rangs
  contextualisés** (zone, profession/spécialité) ; puis V-D + série + points championnat
  + assiduité ; secondaire = différentiel sets/jeux, perf par côté (lié S4).
- **B — Social / fun** : némésis, victime, meilleur binôme, diversité (nb
  adversaires/partenaires/clubs/zones), match le plus serré. Alimenté **aussi par les
  amicaux (S8)**.
- **C — Battles de groupe** (axe fort validé) : Cardio vs Anesthésie, AP-HP vs Cliniques,
  Nord vs Sud → esprit de corps + très partageable Instagram. + classements paire/individuel.
- **D — Communauté/ligue** : agrégats pour la com' (matchs de la journée, top performers,
  plus longue série, spé/zone la plus active).
- **E — Analytique privé** : cote fantôme (S8), qualité d'appariement, affinité, no-show.
**Ton / confidentialité (validé)** : **stats valorisantes publiques, stats gênantes
(némésis) privées par défaut** ; classement officiel public. Reste fidèle à « on ne juge
jamais ses collègues » — tête-à-tête factuel et fun, jamais humiliant.
**Priorisation** : A (perso) d'abord → B (social) → C (battles) → E tourne en silence dès
qu'on a les amicaux.
**Statut** : backlog produit, **non prioritaire** (mode de travail asynchrone).

---

## 1. Objectif global

Lancer la **première ligue de padel des professionnels de santé d'Île-de-France** :
un championnat récurrent (1 match /1-2 semaines), appariement automatique par niveau
et zone, scores saisis en ligne, classements vivants. À ce stade, l'objectif n'est pas
de faire jouer mais de **constituer une communauté d'inscrits qualifiés** (liste
d'attente) et de **valider l'appétence** avant le lancement de la Saison 1.

**Indicateur de succès de la phase actuelle** : nombre d'inscrits sur liste d'attente
+ ratio de partage/parrainage + répartition par zone et par niveau suffisante pour
remplir des appariements crédibles au lancement.

---

## 2. Phases

| Phase | État | Contenu |
|---|---|---|
| **0 — Prototype** | ✅ Fait | Démo locale jouable : inscription, appariement suisse, Elo, scores, classements, mode tournant |
| **1 — Pré-lancement** | 🟡 **EN COURS** | Landing + liste d'attente persistante + sondage + parrainage + Instagram. Reste : RGPD, responsive, countdown, domaine, emails, WhatsApp, com' |
| **2 — Lancement Saison 1** | ⏳ À venir | Ouverture des inscriptions réelles, clubs partenaires, Club des Fondateurs, vraies journées |
| **3 — Croissance** | ⏳ Plus tard | Affinité/ressenti, classements par groupe mis en avant, automatisations, hébergement payant |

> ⚠️ **« Prêt » = uniquement la phase pré-inscription** (landing + liste d'attente, en
> ligne). Le **VRAI lancement (Saison 1, sept 2026) n'est PAS prêt** — gros morceaux non
> construits, à ne pas oublier :
> - **Moteur de jeu réel** : comptes joueurs réels, **open match (S2)**, saisie de score
>   validée, classements réels. *(Aujourd'hui c'est une **démo/simulation**, pas la prod.)*
> - **Emails automatiques (S7)** : confirmation d'inscription + **annonces des étapes** +
>   rappels. **Pas encore en place** (dépend de Brevo + auth domaine).
> - **App iPhone** : **PWA (S6b)** puis natif (S6c). **Pas encore construite.**
> - Restent aussi : côté G/D (S4), amicaux (S8), stats (S9), événements (S10).

---

## 3. Priorités du moment (top 3)

1. **🔴 Conformité RGPD de la page** — bloquant pour toute promo (on collecte des
   emails). Mention de confidentialité + case de consentement.
2. **🔴 Site responsive mobile** — le trafic vient d'Instagram = mobile. Landing
   parfaite sur smartphone avant de pousser la com'. *(S6)*
3. **✅ Domaine `padel-med-league.fr`** — acheté, branché sur Render, HTTPS actif,
   `BASE_URL`/OG sur le `.fr`. Reste la bio Instagram (Nathan). Débloque l'email (S7).

---

## 4. TODO hiérarchisée

### 🔴 Bloquant (avant toute promotion publique)
- [x] **RGPD** : page `/confidentialite` (qui/quoi/pourquoi/durée/droits/contact) +
      **case de consentement** obligatoire (non pré-cochée), **vérifiée côté serveur**
      et **consentement stocké en base** (colonne `consent`, SQLite + Neon). ✅ *fait,
      testé localement — reste à déployer.*
- [x] Vérifier qu'aucun email n'est exposé en query string : OK (POST + redirection sur
      `ok=<code parrainage>`, jamais l'email). ✅
- [x] **Site responsive mobile** : CSS adaptatif (grilles 1 colonne <600px, titres /
      paddings / tables réduits, boutons tactiles). ✅ *fait — à vérifier sur ton tel
      après déploiement.*

### 🟠 Important (cette semaine / semaine prochaine)
- [ ] **Acheter `padel-med-league.fr`** chez OVH (~7-9 €/an, domaine seul). → *Nathan
      (en cours).*
- [x] **Brancher le domaine** sur Render : DNS OVH (A racine + www → `216.24.57.1`),
      HTTPS émis, `BASE_URL` + Open Graph basculés sur `https://padel-med-league.fr`,
      déployé & vérifié. ✅ *fait.* → reste : **bio Instagram** à passer en `.fr` (Nathan).
- [x] **Compte à rebours 1er sept 2026** sur la landing *(S3)* — countdown live dans le
      hero, responsive, « C'est parti ! » à l'échéance. ✅ *fait & déployé.*
- [ ] **Communauté WhatsApp** : la créer → fournir le lien → définir `WHATSAPP_URL`.
      → *Nathan.* (Penser confidentialité : communauté vs canal pour des soignants.)
- [ ] **Publier le post Instagram 01** (annonce) ; photo de profil = `logo-icon.jpg` ;
      mettre l'URL **onrender** en bio tant que le `.fr` n'est pas branché. → *Nathan.*

### Emails *(S7)* — ✅ **ACTIFS** (testé le 24/06/2026)
- [x] Câblé dans `app.py` : confirmation d'inscription brandée (avec lien de parrainage)
      + synchro du contact dans Brevo (liste #3). ✅
- [x] **Compte Brevo** créé (`padelmedleague@gmail.com`). ✅
- [x] **Domaine authentifié** dans Brevo (DKIM brevo1/brevo2 + DMARC + code, via OVH). ✅
- [x] **Alias OVH** `contact@padel-med-league.fr` → forward vers Gmail (sans copie). ✅
- [x] **Variables Render** : `BREVO_API_KEY`, `BREVO_LIST_ID=3`,
      `EMAIL_FROM=contact@padel-med-league.fr`. ✅
- [x] **Test grandeur nature OK** : email de confirmation reçu + contact ajouté. ✅
- [ ] **Annonces d'étapes** = campagnes Brevo vers la liste #3 (quand tu veux). → *Nathan.*
- [ ] Backlog : paliers parrainage, notifications open match, rappels.

### 🟡 À suivre (com' & contenu) — *cf. S11*
- [x] **Mail au SIHP — ENVOYÉ le 25/06/2026.** Accord confirmé (Aude de Loynes, une
      seule communication : newsletter internes + Insta/Facebook). Mail angle
      bénévole/lien/sport + texte à relayer + visuel `01-annonce-newsletter`, lien
      `?from=sihp`. → *Suivi : surveiller les inscrits `from=sihp` dans `/admin`.*
- [ ] **Démarcher les relais** par profession → `CONTACTS-RELAIS.md` (vérifier coord.,
      envoyer, relancer, suivre le tableau). → *Nathan.*
- [ ] Dérouler le **calendrier Instagram** (01 épinglé → 03 à J+2-3 → 02 pour l'urgence).
- [x] **Kit ambassadeur** (textes + one-pager + mail SIHP + cibles + objections) →
      `KIT-AMBASSADEUR.md`. ✅ *fait.*
- [x] **Suivi de source** `?from=` (mesure des relais) visible dans l'admin. ✅ *fait.*
- [x] **Viralité** *(S11)* : ✅ **fait** sur la page de succès — (a) CTA dédié
      **« invite ton binôme »** (message WhatsApp taillé pour le 2v2), (b) **rang de
      parrain + podium anonymisé** (gamification RGPD-safe : on n'expose aucun nom
      tiers, seulement ton rang + les compteurs du top 3), (c) **carte perso
      partageable** (`/carte?ref=` → carte SVG « Membre fondateur » à screenshoter en
      story + `/carte.svg`) et (d) **OG personnalisé** sur les liens partagés
      (« Prénom t'invite… »). Reste en backlog : classement ambassadeurs *public*
      (volontairement écarté tant qu'on n'a pas d'opt-in nominatif — cf. RGPD).

### 🟢 Backlog produit (Saison 1+)
- [ ] **Modèle « open match »** *(S2)* : ouverture de match par un joueur + sollicitation
      des compatibles + fenêtre d'élargissement + sièges solo/duo. Spéc → PLAN.md.
- [ ] **Matchs amicaux + cote fantôme** *(S8)* : débloqués après l'officiel, hors
      classement, comptés en stats fun + shadow rating privé. Dépend de S2.
- [ ] **Statistiques joueur/groupe** *(S9)* : dashboard perso (A) → social/fun (B) →
      battles de groupe (C). Construit sur l'existant `stats_joueurs`/`classement_par`.
- [ ] **Profil : côté G/D + tolérance 0-10** *(S4)* → schéma joueur + moteur d'appariement.
- [ ] **PWA** *(S6b)* : rendre le site installable (écran d'accueil + push).
- [ ] Score d'**affinité / ressenti de match** + quota d'exploration anti-bulle.
- [ ] Mise en avant des **classements par groupe** (profession, spécialité, structure,
      zone).
- [ ] **Clubs partenaires** + avantages Club des Fondateurs (50 premières équipes).
- [ ] Passage **Render payant** ($7/mo, sans veille) au lancement réel.
- [ ] **App native iOS** *(S6c)* — phase Croissance seulement.
- [ ] **Google Sign-in** *(S5)* — déprioritisé ; réactivable via `GOOGLE_CLIENT_ID`.
- [ ] Refactor éventuel si le produit décolle (templates, tests).

### ⛔ Explicitement EXCLU
- **Scraping d'adresses `prenom.nom@aphp.fr` + cold-emailing de masse.** Illégal
  (RGPD/ePrivacy), risque de blacklist du domaine et d'image négative. Ne pas
  construire d'outil pour ça. → Alternative : ambassadeurs + relais officiels.

---

## 5. Prochaines étapes concrètes (1-2 semaines)

1. **Claude** : **RGPD** (mention + consentement) + **responsive mobile** + **countdown
   1er sept** sur la landing. → débloque la promo.
2. **Nathan** : finaliser l'**achat du domaine** chez OVH → me prévenir pour le DNS Render.
3. **Claude** : domaine actif → brancher Render + basculer `BASE_URL` / OG / bio sur `.fr`.
4. **Nathan** : créer le **compte Brevo** + l'**alias `contact@`** → je fournis les DNS
   email (SPF/DKIM/DMARC) et je câble l'envoi (confirmation d'inscription d'abord).
5. **Nathan** : créer la **communauté WhatsApp**, publier le **post 01** et démarrer le
   **démarchage institutionnel** avec le kit ambassadeur.

---

## 6. Actions Nathan en attente (récap rapide)

| # | Action | Statut |
|---|---|---|
| 1 | ~~Acheter + brancher `padel-med-league.fr`~~ | ✅ acheté, branché, HTTPS actif, site en `.fr` |
| 1b | ~~Passer la **bio Instagram** sur `padel-med-league.fr`~~ | ✅ en ligne (`/?from=ig`, vérifiée 25/06) |
| 2 | ~~Alias OVH `contact@` + compte Brevo + auth domaine + env Render~~ | ✅ **emails actifs (testé)** |
| 3 | ~~Définir **`APERCU_CODE`** dans Render~~ | ✅ fait |
| 4 | **Créer la CHAÎNE WhatsApp** (anti-spam, numéros privés) → coller le lien `whatsapp.com/channel/…` dans `WHATSAPP_URL` (Render). Mode d'emploi : [COMMUNAUTE-WHATSAPP.md](COMMUNAUTE-WHATSAPP.md) §2 | ⏳ (remplace l'ancien groupe) |
| 5 | Envoyer le **mail SIHP** (`/?from=sihp`) + publier **post 01** + photo de profil = nouveau `logo-icon` | ⏳ |

> 📧 **Email** : `padelmedleague@gmail.com` créé = bon **inbox/ops**. Public/envoi : utiliser
> `contact@padel-med-league.fr` (alias OVH → ce Gmail) pour rester pro et **authentifiable**
> (SPF/DKIM/DMARC). Voir S7.
> 🐍 **Logo** : refait en serpent monochrome (caducée) — fichiers SVG/PNG/JPG à jour.

---

## 7. Coûts (ordre de grandeur) — *estimation 23/06/2026*

> Principe : **les terrains sont payés par les joueurs** (ils réservent eux-mêmes) →
> la plateforme ne paie que la **tech** + d'éventuels frais ponctuels. Coûts bas.

| Poste | Liste d'attente (maintenant) | Lancement (lean) | Si ça grossit |
|---|---|---|---|
| Domaine `.fr` (OVH) | ~8 €/an | ~8 €/an | ~8 €/an |
| Hébergement Render | 0 € (free) | ~7 $/mo (Starter) | ~25 $/mo |
| Base Neon (Postgres) | 0 € (free) | 0 € (free) | ~19 $/mo |
| Emails Brevo | — | 0 € (free 300/j) | ~19 €/mo |
| Push (PWA) | — | 0 € | 0 € |
| **Total tech** | **~8 €/an** | **~10 €/mo (~120 €/an)** | **~40-70 €/mo (~500-800 €/an)** |

**Frais ponctuels possibles (optionnels)** : lots Club des Fondateurs (souvent fournis
par les clubs partenaires → potentiellement 0 €), structure asso loi 1901 (gratuite) +
assurance événementielle (modeste, si formalisation), app native iOS (99 $/an, repoussée),
outils com' type Canva (~12 €/mo, optionnel).

**À retenir** : on lance pour **~10 €/mois** ; le coût ne monte que si la ligue grossit.
Le « coût » dominant n'est pas les serveurs mais **le temps** (Nathan + ambassadeurs).
Coûts évités en restant malin : **PWA** (pas de natif), **terrains payés par les joueurs**,
**tiers gratuits** tant qu'ils suffisent.

---

## 8. Readiness PRÉ-INSCRIPTION — vérifié le 24/06/2026

> Audit complet passé au vert (tests automatisés de bout en bout). La **phase
> pré-inscription** est prête à être promue. *(Rappel : le VRAI lancement Saison 1 reste
> à construire — cf. encart §2.)*

**✅ Vérifié & en ligne sur `padel-med-league.fr`**
- Identité : **logo caducée** dans le header + **favicon** ; ancien emoji retiré.
- Landing : hero « débutant **ou** confirmé, à ton niveau » ; section niveau remontée ;
  « Comment ça marche » à jour (solo/équipe au choix + amicaux) ; aucune réf. obsolète.
- RGPD : consentement obligatoire (vérifié serveur) + page `/confidentialite`.
- Sécurité : `/admin` et la démo **protégés** (verrou aperçu) → plus de fuite d'emails.
- Compteur masqué <50 · compte à rebours 1ᵉʳ sept · WhatsApp · suivi de source `?from=`.
- Mobile responsive · HTTPS · domaine `.fr`.
- Emails : **code prêt** (confirmation + contact Brevo), activation = clé Brevo (Nathan).

**⏳ Avant de lancer la promo — actions Nathan**
1. Activer **Brevo** (clé + DNS DKIM/DMARC + env Render) → emails de confirmation actifs.
2. **Bio Instagram** → `padel-med-league.fr/?from=ig` + **photo de profil = `logo-icon`**.
3. Programmer la **com'** en une session → voir `CALENDRIER-COMM.md` (calendrier 10 sem.
   pré-écrit + scheduler gratuit). Envoyer le **mail SIHP** (`/?from=sihp`).

> Tant que les emails de confirmation ne sont pas activés (Brevo), on **peut** déjà
> promouvoir (l'inscription marche), mais l'inscrit ne reçoit pas d'accusé de réception.
> **Reco : activer Brevo AVANT la promo** (c'était la demande).
