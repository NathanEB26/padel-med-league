# MEMOIRE.md — Journal des décisions

> Pourquoi le projet est ce qu'il est. Chaque entrée = **décision + raison +
> alternatives écartées / compromis**. À compléter (ne pas réécrire) au fil du temps.
> Architecture courante → [CLAUDE.md](CLAUDE.md). Cap & roadmap → [STRATEGIE.md](STRATEGIE.md).

---

## Décisions architecturales

### D1 — Python stdlib, monofichier, zéro dépendance obligatoire
**Décision** : `http.server` + `sqlite3`, tout dans `app.py`.
**Pourquoi** : Nathan a peu d'expérience du code ; il fallait un truc qui **tourne
en `python3 app.py`** sans installation, facile à lancer en local pour valider le
concept. Un framework (Flask/Django) aurait ajouté une barrière d'installation et de
la complexité inutile à ce stade.
**Compromis accepté** : HTML écrit à la main (verbeux), pas d'ORM, pas de tests
automatisés. Acceptable tant qu'on est en prototype.

### D2 — Deux bases : SQLite (démo) + PostgreSQL/Neon (liste d'attente)
**Décision** : la démo produit tourne en SQLite (éphémère) ; la **liste d'attente et
les parrainages** vont dans Neon si `DATABASE_URL` existe.
**Pourquoi** : sur Render free, le disque est **éphémère** → un redéploiement
effacerait les inscrits. Inacceptable pour une liste d'attente (c'est l'actif le plus
précieux de la phase pré-lancement). Neon (Postgres gratuit) résout ça.
**Preuve faite** : test d'insertion → commit marqueur → redéploiement → l'entrée a
**survécu** → suppression via l'outil admin. Persistance confirmée.
**Compromis** : double code path (PG vs SQLite) dans chaque fonction waitlist.

### D3 — Activation conditionnelle par variable d'environnement
**Décision** : Neon, Google Sign-in, WhatsApp s'activent **seulement** si leur env var
est définie ; sinon repli gracieux (fonction masquée / SQLite).
**Pourquoi** : permet de **déployer en continu** sans tout configurer d'un coup, et à
Nathan d'activer chaque brique quand il est prêt, sans toucher au code.

### D4 — Système suisse pour l'appariement (pas de poules figées)
**Décision** : appariement **suisse**, recalculé chaque journée par minimisation de
coût (écart de niveau + distance de zone + anti-revanche).
**Pourquoi** : Nathan veut un appariement **100 % automatique** qui **s'ajuste aux
résultats**. Le suisse fait jouer des adversaires de niveau proche sans avoir à
constituer des poules à l'avance, et s'adapte semaine après semaine.
**Alternative écartée** : poules/divisions fixes (trop rigides, mauvais au démarrage
quand les niveaux sont incertains).

### D5 — Zones cardinales par densité de clubs (pas les départements)
**Décision** : 9 zones boussole (Centre + 8 directions), mappées à la **densité de
terrains de padel**, avec détection assistée par code postal.
**Pourquoi** : correction explicite de Nathan — découper par département n'a pas de
sens pour le padel (les clubs ne suivent pas les frontières administratives). Ce qui
compte, c'est « un adversaire **près de chez moi** », donc la géographie réelle des
terrains.

### D6 — Niveau : 4 portes d'entrée + cote Elo dynamique
**Décision** : à l'inscription, 4 façons de déclarer son niveau (échelle 3-7,
classement FFT, résultats tournoi, questionnaire) ; ensuite une **cote Elo** évolue
avec les résultats.
**Pourquoi** : accueillir aussi bien le joueur qui « connaît son classement » que le
débutant qui ne sait pas se situer, sans friction. L'Elo corrige les erreurs
d'auto-évaluation au fil du temps.

### D7 — Inscription individuelle + appariement de binôme (pas d'inscription en équipe)
**Décision** : on s'inscrit **seul**, puis on s'apparie via recherche par
mail/nom d'utilisateur.
**Pourquoi** : correction de Nathan. Beaucoup de gens n'ont **pas** de binôme prêt ;
exiger une équipe à l'inscription = barrière. On capte l'individu d'abord, on aide à
former le binôme ensuite.

### D8 — Modèle de ligue UNIFIÉ (solo OU équipe au choix par journée)
**Décision** : une seule ligue ; chaque journée, le joueur choisit solo (partenaires
tournants, Americano) ou équipe (binôme fixe). Deux classements.
**Pourquoi** : on ne savait pas si le public préférerait solo ou équipe — et le
sondage devait trancher. Le modèle unifié **supprime le dilemme** : pas besoin de
choisir une formule pour toute la ligue, chacun module selon ses envies/dispos.
Insight terrain : les débutants veulent essayer sans s'engager, les bons veulent
trouver leur niveau + des affinités sociales → le solo tournant abaisse la barrière,
l'équipe fidélise.

### D9 — Anti-bulle : ressenti de match, pas notation des pairs
**Décision** : à terme, score d'affinité qui refait jouer ensemble des gens qui se
sont bien entendus, **avec quota d'exploration** ; on note **son ressenti**, jamais
ses partenaires/adversaires.
**Pourquoi** : correction de Nathan — noter des collègues (par ailleurs confrères dans
la vraie vie) est socialement toxique et juridiquement délicat. Noter son propre
ressenti capte le même signal sans pointer personne. Le quota d'exploration évite que
les groupes se referment.
**Statut** : prévu Saison 1-2, pas encore implémenté.

### D10 — Cible élargie : tous les soignants
**Décision** : passer de « médecins » à **tous les professionnels de santé**.
**Pourquoi** : marché plus large, plus de densité pour remplir les zones et les
niveaux, et plus inclusif. Le naming technique legacy (`padel-med-league`) reste pour
ne pas casser les liens/dépôt, mais **tout le discours** est élargi.

### D11 — Hébergement Render (free) + domaine .fr plus tard
**Décision** : Render plan free maintenant ; achat + branchement de
`padel-med-league.fr` ensuite ; passage Render payant ($7/mo, sans veille) au vrai
lancement.
**Pourquoi** : le free suffit pour une liste d'attente (le réveil ~50 s est tolérable).
Inutile de payer tant qu'il n'y a pas de trafic réel. Acheter le domaine tôt sécurise
quand même le nom.

### D12 — Design « LIV Golf / Kings League »
**Décision** : thème sombre néon (fond `#070b10`, lime `#c6ff00`, magenta, or), titres
900 italic.
**Pourquoi** : référence visuelle donnée par Nathan — un rendu « claquant », sportif,
moderne, pour se démarquer d'un site institutionnel médical et donner envie aux jeunes
soignants. Cohérence landing ↔ visuels Instagram ↔ logo.

---

## Problèmes rencontrés & solutions

| Problème | Cause | Solution |
|---|---|---|
| **Homebrew cassé** (macOS 26.5.1, `MacOSVersionError`) | Brew ne reconnaît pas macOS 26 | Téléchargement direct du binaire `gh` depuis GitHub Releases → `~/.local/bin/gh` |
| **Render « Deployed » mais 404** (`x-render-routing: no-server`) | Email Render **non vérifié** | Nathan a vérifié son email → site live |
| **Dashboard Render bloqué** pour l'extension Chrome | « Navigation to this domain is not allowed » | Étapes Render faites **manuellement** par Nathan |
| **Fonction `options` cassée / `opts` indéfini** | Stub mort `def options(...): pass` + appel à `opts()` non défini | Renommé le vrai helper en `opts(liste, sel=None)`, supprimé le stub |
| **Fuite de connexions DB** dans la vue classement individuel | `nom_equipe(db(), …)` appelé **par ligne** | Préchargement des noms d'équipe une seule fois dans un dict |
| **Débordement de texte dans les SVG** (pills/CTA) | Rectangles trop étroits, police trop grande | Élargi les `rect`, réduit la police/letter-spacing, vérifié visuellement sur PNG |
| **Emojis dans les SVG** | Risque de rendu incohérent selon le moteur | Emojis retirés des SVG (gardés dans les légendes texte) |

---

## Compromis assumés (dette consciente)

- **HTML en chaînes Python** : verbeux, pas idéal à maintenir → acceptable en
  prototype, à refactorer si le produit décolle.
- **Données démo éphémères (SQLite)** : OK, ce ne sont que des données de simulation.
- **Pas de tests automatisés** : vérification manuelle / visuelle pour l'instant.
- **Naming legacy `med`/`ligue.db`** alors que la cible est tous les soignants :
  garder pour ne pas casser dépôt/URL ; le discours public est élargi.
- **Render free (réveil ~50 s)** : toléré en phase liste d'attente.

---

## Évolutions majeures (chronologie condensée)

1. Idée initiale : ligue de padel pour **médecins** IdF, match /15j, appariement
   niveau+zone, scores en ligne.
2. Plan détaillé (`PLAN.md`) → prototype local (`app.py`, SQLite).
3. Appariement **suisse** + cote **Elo** + **zones cardinales** + détection CP.
4. Inscription **individuelle** + appariement de binôme + structure d'exercice.
5. Design **LIV/Kings** ; déploiement **GitHub + Render**.
6. Généralisation **médecins → tous soignants** + stratégie de **communication**.
7. **Landing de conversion** + **liste d'attente** + **sondage** solo/équipe.
8. **Parrainage** à paliers + **partage** multi-canal + **Open Graph**.
9. Mode **tournant (Americano)** + classements **individuels & par groupe**.
10. **Modèle unifié** (solo/équipe au choix) + ressenti de match anti-bulle.
11. **Persistance Neon** (vérifiée) + **Google Sign-in** + **communauté WhatsApp**
    (les deux derniers en attente d'activation par Nathan).
12. **Instagram** `@padelmedleague` : logo, 3 visuels, légendes, calendrier.
