# Mettre la démo en ligne (Render — gratuit, 24/7)

Le code est sur GitHub : https://github.com/NathanEB26/padel-med-league
Le fichier `render.yaml` configure tout automatiquement. Il ne reste qu'à créer
le service sur Render.

## Étapes (≈ 3 minutes)

1. Aller sur **https://render.com** → **Get Started** (ou **Sign In**).
2. Choisir **Sign in with GitHub** → autoriser Render à accéder à vos dépôts.
   (Si demandé, autorisez l'accès au dépôt `padel-med-league`.)
3. Dans le tableau de bord Render : bouton **New +** (en haut à droite) →
   **Blueprint**.
4. Sélectionner le dépôt **padel-med-league** → **Connect**.
5. Render lit `render.yaml` et propose le service **padel-med-league** (plan
   **Free**). Cliquer **Apply** (ou **Create**).
6. Le déploiement démarre (logs visibles). Patienter **2 à 3 minutes** jusqu'à
   **Live**.
7. L'URL publique s'affiche en haut, du type :
   **https://padel-med-league.onrender.com** → c'est votre démo en ligne, à
   partager !

## Bon à savoir (offre gratuite Render)

- **Mise en veille** : après ~15 min sans visite, le service s'endort. La
  première visite suivante prend **~50 secondes** à réveiller (normal), puis
  c'est rapide. Pour une démo, ouvrez l'URL 1 min avant de la montrer.
- **Données non permanentes** : la base de démo se **réinitialise** à chaque
  redéploiement/réveil profond. Les équipes saisies pendant une démo peuvent donc
  disparaître. C'est volontaire et sans risque pour montrer le produit.
- **Mises à jour** : tout nouveau `git push` sur GitHub redéploie
  automatiquement le site.

## En cas de souci
Copier les logs affichés par Render et me les envoyer — je corrige.
