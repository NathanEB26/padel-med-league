# REPRISE.md — Rituel de reprise de session

> Déclenché quand Nathan écrit **« On reprend »** (ou variante explicite, ex.
> « on reprend le projet padel »). Symétrique du rituel de fin de session
> (« Au revoir », protocole en mémoire Cowork). Ce fichier vit **dans le
> repo** : il est donc lu **dans les deux environnements** ([CLAUDE.md](CLAUDE.md)
> pointe ici), mais le **contenu du rituel diffère selon le contexte** (voir
> §0) — Nathan travaille les deux en parallèle, sur des sujets différents :
>
> - **Cowork** → réflexion **stratégie globale** du projet + **communication**.
> - **Claude Code** → **mise en place concrète du site** (code, déploiement, bugs).

---

## 0. Identifier le contexte avant de dérouler le protocole

- Session dans **Cowork** → suivre **§A (Stratégie & communication)**.
- Session dans **Claude Code** → suivre **§B (Mise en place technique)**.
- Si Nathan amène un sujet qui ne correspond pas au contexte habituel de l'outil
  (ex. une question stratégique posée dans Code, ou un bug remonté dans Cowork),
  traiter quand même la demande normalement — la séparation organise *où on
  pense faire quoi par défaut*, ce n'est pas une barrière stricte.

---

## 0bis. Vérifier la boîte à idées Notion (si connecté)

Avant de dérouler §A ou §B : si l'outil Notion est disponible dans la session,
consulter la page **« 📥 Idées & to-do — Ligue Padel (mobile) »**
(https://app.notion.com/p/38c48ae1d1da818b8e00c84331552ba7). C'est l'inverse du
Dashboard (qui est un miroir en lecture) : **Nathan l'édite lui-même**, souvent
depuis son téléphone en dehors d'une session — c'est une vraie source d'entrée.

- Lire la section « À trier ».
- Intégrer ce qui a de la substance dans le bon fichier projet (`STRATEGIE.md`
  pour stratégie/com', le code/`CLAUDE.md` pour le technique, etc.) et signaler
  à Nathan où chaque item a été rangé.
- Une fois intégré, **vider la section « À trier »** côté Notion — la page
  reste une boîte de capture, pas un historique qui s'accumule.
- Si un item ne semble pas encore mûr ou actionnable, le laisser tel quel
  plutôt que de le supprimer ou de le ranger en force.
- Si Notion n'est **pas connecté** dans la session (ex. certaines sessions
  Claude Code sans le connecteur), le signaler à Nathan plutôt que de supposer
  qu'il n'y a rien de nouveau.

---

## §A — Cowork : stratégie & communication

1. **Relire l'état du projet** :
   - [STRATEGIE.md](STRATEGIE.md) — « Décisions stratégiques » (dernières entrées),
     « Priorités du moment », la partie 🟡 *« À suivre (com' & contenu) »* de la TODO.
   - [CALENDRIER-COMM.md](CALENDRIER-COMM.md) — où on en est dans le calendrier
     (quelle semaine S1→S10, quels posts/relais sont dus).
   - [CONTACTS-RELAIS.md](CONTACTS-RELAIS.md) — tableau de suivi (contactés /
     relancés / ont relayé).
   - [MEMOIRE.md](MEMOIRE.md) si pertinent au sujet du jour.

2. **Vérifier l'état réel plutôt que les docs seuls**, quand c'est vérifiable
   rapidement : boîte Gmail (mails réellement envoyés/reçus), Instagram et
   WhatsApp en direct (pas seulement ce que dit le doc), tableau `/admin`
   (inscrits par `?from=`). Les docs peuvent être en retard sur la réalité —
   cf. principe « vérifier les canaux live, pas seulement les docs ».

3. **Point rapide en 3 temps** :
   - Où on en est (la com' est priorité n°1 actuelle — S13 ; le produit S12
     reste en attente, échéance ferme début août, à ne pas perdre de vue).
   - Ce qui s'est passé depuis la dernière session (dernières entrées
     STRATEGIE.md/CONTACTS-RELAIS.md, ou ce que Nathan rapporte).
   - Prochaines actions concrètes : relances dues, prochain post à publier,
     prochaine cible de relais à démarcher.

4. **Ne pas refaire un travail déjà fait** : vérifier le tableau de suivi avant
   de proposer de contacter une structure déjà contactée, ou de reprogrammer un
   post déjà publié.

5. **Dérouler §C** (briefing + mode d'exécution autonome).

---

## §B — Claude Code : mise en place technique du site

1. **Relire l'état du projet** :
   - [CLAUDE.md](CLAUDE.md) — architecture (carte de `app.py`), règles non
     négociables.
   - [STRATEGIE.md](STRATEGIE.md) — section 🔴 *« Priorité produit — échéance
     début août »* (S12 : open match + matchs amicaux), TODO technique en
     cours/backlog.
   - `git log` — état réel du code (peut être en avance ou en retard sur ce
     que dit STRATEGIE.md).

2. **Vérifier l'état réel plutôt que les docs seuls** : dernier commit, statut
   du déploiement Render, site effectivement en ligne, variables d'env actives
   (`DATABASE_URL`, `BREVO_API_KEY`…). Ne pas supposer qu'une case ✅ dans
   STRATEGIE.md est encore vraie si le code la contredit.

2bis. **Pousser les commits en attente.** Faire `git status` / `git log
   origin/main..HEAD` : si des commits faits depuis Cowork attendent (le
   réseau sandboxé y bloque `git push`, voir AU-REVOIR.md point 5), les
   pousser **dès le début de la session**, avant de continuer — ne pas attendre
   la fin de session pour s'en apercevoir.

3. **Point rapide en 3 temps** :
   - Où en est l'échéance S12 (open match + amicaux, début août).
   - Ce qui a été codé/déployé depuis la dernière session.
   - Prochaine brique technique à construire, bugs connus.

4. **Ne pas refaire un travail déjà fait** : vérifier l'état actuel du code
   avant de proposer une implémentation (ex. ne pas ré-implémenter une feature
   déjà en place).

5. **Dérouler §C** (briefing + mode d'exécution autonome).

---

## §C — Briefing du jour + mode d'exécution autonome (commun §A et §B)

### 1. Briefing du jour — actions Nathan en attente

Produire systématiquement ce bloc à la fin du point rapide :

```
## Tes actions du jour (côté toi)
1. [action prioritaire Nathan — ex. créer la Page LinkedIn]
2. [action bloquante — ex. acheter le domaine]
3. …
```

**Source** : lire **STRATEGIE.md §6 « Actions Nathan en attente »** + les items
marqués *→ Nathan* dans la TODO (🟠/🟡). Trier par priorité du jour, pas par
ordre d'apparition dans le fichier. Ne garder que ce qui est **réellement en
attente** (pas les cases déjà cochées).

### 2. Mode d'exécution autonome

**Règle** : après le point rapide et le briefing, **attaquer d'office la
première tâche non bloquante non sensible** identifiée dans la session.

- **Proposer l'approche** (1-2 phrases : ce qu'on va faire, pourquoi), puis
  **exécuter sans relance intermédiaire**.
- Ne remonter à Nathan **que** :
  - les arbitrages stratégiques non décidés,
  - les actions qui lui sont réservées (achat, création de compte, saisie de
    mot de passe, contact à démarcher, validation légale).
- Pour tout le reste : coder, commiter, déployer, mettre à jour les docs — et
  signaler ce qui a été fait **en fin d'action**, pas avant.

**Seuil** : « proposer puis exécuter » — pas « demander si c'est ok », pas
« attendre une confirmation » entre deux sous-tâches d'un même chantier. Si
Nathan veut stopper ou pivoter, il le dit.

---

## Pourquoi un seul fichier, avec deux sections

Le fichier reste **unique et partagé dans le repo** (pas de mémoire propre à
une plateforme) pour que le rituel se déclenche **pareil partout** — même
commande « On reprend », même fichier lu via [CLAUDE.md](CLAUDE.md). Mais son
**contenu** reflète maintenant que Nathan **sépare volontairement les deux
contextes** : Cowork porte la réflexion stratégie/communication, Code porte la
construction concrète du site. Le découpage §A/§B évite qu'une session Code
parte sur du brainstorm com', ou qu'une session Cowork parte sur du debug de
code.

Si cette séparation évolue, modifier ce fichier (pas la mémoire Cowork) pour
que le changement profite aux deux contextes.
