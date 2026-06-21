# Mode d'emploi — Prototype local

Ceci est une **simulation** de la Ligue de Padel des Médecins d'Île-de-France,
qui tourne sur votre propre ordinateur (rien n'est publié sur internet).

## Démarrer

**Option 1 (la plus simple)** : double-cliquez sur **`Lancer la ligue.command`**.
Une fenêtre noire (Terminal) s'ouvre — laissez-la ouverte.

**Option 2** : dans le Terminal, tapez `python3 app.py` depuis ce dossier.

Puis ouvrez votre navigateur sur : **http://localhost:8000**

> Si un double-clic affiche un avertissement de sécurité macOS : clic droit sur
> le fichier → « Ouvrir » → « Ouvrir » (à faire une seule fois).

## Arrêter
Fermez la fenêtre Terminal, ou appuyez sur **Ctrl+C** dedans.

## Ce que vous pouvez tester
- **Classement** : les 12 équipes de démonstration, mises à jour en direct.
- **Calendrier** : les journées et leurs matchs ; bouton « Saisir le score ».
- **Inscription** : créer une nouvelle équipe (2 joueurs, statut + spécialité).
- **Estimer mon niveau** : le questionnaire (porte D) qui calcule un niveau 3-7.
- **Admin → Générer la journée** : déclenche l'**appariement suisse** automatique
  (niveau + zone + anti-rematch). Regardez les nouveaux matchs apparaître.
- **Admin → Réinitialiser** : repart des données de démonstration.

## Bon à savoir
- C'est un **prototype** pour valider le fonctionnement, pas la version finale.
  Le design et l'hébergement en ligne viendront ensuite.
- Toutes les données sont dans le fichier `ligue.db` (sur votre Mac uniquement).
  Le supprimer puis relancer recrée une démo neuve.
