# COMMUNAUTE-WHATSAPP.md — Organisation de la communauté WhatsApp

> Décidé le 25/06/2026. Format retenu : **Chaîne WhatsApp** en pré-lancement,
> **Communauté + sous-groupes par zone** au lancement (Saison 1). Voir aussi
> [COMMUNICATION.md](COMMUNICATION.md) et [STRATEGIE.md](STRATEGIE.md) (S11).

---

## 1. Pourquoi une Chaîne (et pas un groupe) en pré-lancement

Le besoin n°1 aujourd'hui = **prévenir tout le monde de façon fiable** (les emails
peuvent finir en spam/Promotions). Public = soignants → **sensibles à la
confidentialité de leur numéro**.

| Critère | Groupe | Communauté | **Chaîne ✅** |
|---|---|---|---|
| Numéro de l'abonné visible | ❌ visible par tous | partiellement | ✅ **anonyme** |
| Annonces fiables (anti-spam) | oui mais noyé | oui | ✅ **parfait** |
| Modération | lourde | moyenne | ✅ **nulle** |
| Scale (centaines/milliers) | non (1024 max) | oui | ✅ **illimité** |
| Interaction / trouver un binôme | oui | oui (sous-groupes) | ❌ 1-sens |

En pré-lancement, il n'y a pas encore de matchs à organiser : l'interaction n'est pas
utile, la **fiabilité + la confidentialité** priment. → **Chaîne.**

L'interaction (trouver des partenaires par zone) devient utile **au lancement** → on
ajoutera alors une **Communauté** avec un **sous-groupe par zone**.

---

## 2. Créer la Chaîne (à faire par Nathan)

1. WhatsApp → onglet **Actus** (Updates) → **+** → **Créer une chaîne**.
2. **Nom** : `Ligue Padel Santé · IDF`
3. **Description** :
   > Le championnat de padel des soignants d'Île-de-France. Annonces officielles :
   > ouverture, créneaux, clubs partenaires. Infos seulement, ton numéro reste privé.
   > Inscription → padel-med-league.fr
4. **Photo** : `visuels-instagram/logo-icon.jpg` (la même que l'Instagram → cohérence).
5. Récupérer le **lien de la chaîne** (Partager le lien → `https://whatsapp.com/channel/…`).
6. **Coller ce lien dans `WHATSAPP_URL`** sur Render (remplace l'ancien lien de groupe).
   → le site et l'email basculent automatiquement sur « Suis le canal ».

> ⚠️ Le lien actuel dans le code pointe vers un **groupe** (numéros exposés). À
> remplacer par le lien de la **chaîne** avant de pousser la promo.

### Anonymat de l'admin (confirmé par WhatsApp)

Sur une Chaîne, **l'admin n'est jamais mis en avant**. WhatsApp ne montre aux abonnés
**ni ton numéro, ni ta photo de profil, ni ton nom de profil WhatsApp** — ils ne voient
que le **nom** et la **photo de la chaîne**. Donc :
- Nommer la chaîne `Ligue Padel Santé · IDF` (pas un nom de personne) suffit à rester
  en coulisse. Photo = le logo caducée.
- **Si on ajoute des co-admins** (ambassadeurs) : eux verront le numéro de l'admin
  (les admins se voient entre eux) ; les abonnés, non.
- **Séparation totale (optionnel)** : créer la chaîne depuis un **numéro dédié**
  (2ᵉ SIM/eSIM ou WhatsApp Business) si on ne veut aucun lien avec le compte perso.

> Réf. : WhatsApp Help Center — « About safety and privacy on channels ».

---

## 3. Ligne éditoriale (quoi publier, à quel rythme)

**Rythme pré-lancement : 1 post / semaine** (pas plus — une chaîne silencieuse vaut
mieux qu'une chaîne qui spamme et fait désabonner). Toujours **utile ou exclusif**.

- **Post de bienvenue** (épinglé) — voir §4.
- **Jalons d'inscription** : « On est 50 / 100 / 200 inscrit(e)s 🎾 ».
- **Coulisses** : un club partenaire qu'on contacte, le format expliqué, une zone qui
  se remplit.
- **Compte à rebours** : J-60, J-30, J-7 avant le 1ᵉʳ septembre 2026.
- **Appels à l'action ponctuels** : « Tag ton binôme », « Partage en story » (renvoyer
  vers la carte perso `/carte`).
- **Au lancement** : ouverture des inscriptions réelles + lien vers les sous-groupes de
  zone.

À **éviter** : messages sans valeur (« bonjour à tous »), trop de fréquence, contenu
médical/pro (rester sur le padel et la ligue).

---

## 4. Messages prêts à l'emploi

**Post de bienvenue (à épingler dès la création) :**
> 🎾🩺 Bienvenue dans le canal officiel de la **Ligue Padel Santé Île-de-France** !
> Ici, et seulement ici, tu reçois les annonces qui comptent : date d'ouverture,
> créneaux, clubs partenaires, Club des Fondateurs. Pas de spam, ton numéro reste
> privé. Coup d'envoi de la Saison 1 : **1ᵉʳ septembre 2026**.
> Pas encore inscrit(e) ? → padel-med-league.fr

**Relance jalon (exemple) :**
> 🔥 On vient de passer les **100 soignant(e)s** sur la liste ! Médecins, kinés,
> infirmier(ère)s, dentistes, sages-femmes, étudiant(e)s… la ligue prend forme.
> Invite ton binôme de padel, vous serez appariés ensemble : padel-med-league.fr

**J-30 :**
> ⏳ Plus que **30 jours** avant le coup d'envoi. Les 50 premières équipes inscrites
> entrent au **Club des Fondateurs** (badge + accès prioritaire). C'est le moment
> d'embarquer ton binôme 🎾

---

## 5. Au lancement (Saison 1) — passer à la Communauté

Quand les inscriptions réelles ouvrent et que les gens doivent **trouver des
partenaires** :

1. Créer une **Communauté WhatsApp** `Ligue Padel Santé · IDF`.
2. Groupe **« 📣 Annonces »** (admin only) = reprend le rôle de la chaîne pour les
   membres actifs.
3. **Sous-groupes par zone** (les 9 zones cardinales : Centre + N/NE/E/SE/S/SO/O/NO),
   **créés à la demande** quand une zone atteint ~15-20 inscrits (sinon groupes vides).
4. **Charte épinglée** dans chaque groupe (voir §6).
5. **Modérateurs** : Nathan + 1 ambassadeur(rice) par zone active (cf. KIT-AMBASSADEUR).

> La chaîne reste en parallèle comme **vitrine publique anti-spam** ; la communauté
> sert l'**organisation des matchs**.

---

## 6. Charte (à épingler dans les groupes, au lancement)

> **Bienvenue ! Ici on parle padel, pas médecine.** Règles simples :
> 1. Respect & bienveillance — on est entre collègues de tous horizons.
> 2. **On ne sollicite pas d'avis médical** ni de patientèle. Zone padel uniquement.
> 3. Pas de spam, pas de pub, pas de démarchage.
> 4. Pour trouver un match : indique ta **zone**, ton **niveau** et tes **dispos**.
> 5. On ne note jamais ses partenaires — seulement son propre ressenti (sur le site).
> Tu ne respectes pas la charte → retrait du groupe. Bon jeu 🎾

---

## 7. Confidentialité (rappel RGPD)

- **Chaîne** : abonnés anonymes entre eux → rien à signaler.
- **Groupes** (au lancement) : les numéros sont **visibles entre membres du même
  groupe**. → le préciser au moment de rejoindre (« en rejoignant ce groupe, ton
  numéro sera visible des autres membres »). Ne jamais importer/ajouter quelqu'un sans
  son accord.
- Aucun export de numéros, aucun usage hors organisation de la ligue.
