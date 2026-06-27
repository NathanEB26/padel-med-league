# AU-REVOIR.md — Rituel de fin de session

> Déclenché quand Nathan écrit **« Au revoir »** (signal qu'il ferme et
> reprendra plus tard). Symétrique de [REPRISE.md](REPRISE.md). Vit dans le
> repo pour fonctionner **identiquement en Cowork et en Claude Code** — avant,
> ce rituel vivait uniquement dans la mémoire auto-persistante de Cowork,
> invisible pour Code.

---

## Protocole

1. **Mettre à jour les fichiers** si la session a produit quelque chose à
   retenir :
   - [STRATEGIE.md](STRATEGIE.md) — TODO cochée/ajoutée, priorités revues,
     nouvelle décision stratégique si tranchée pendant la session.
   - [MEMOIRE.md](MEMOIRE.md) — décision architecturale/produit notable.
   - **Seulement en Cowork** : la mémoire auto-persistante, pour les faits
     utiles aux sessions futures qui ne sont pas du ressort du repo (statut
     vivant des canaux externes, préférences de travail de Nathan, etc.).
   - Tout ce qui compte doit finir **dans un fichier** — pas seulement dans le
     contexte de la conversation, qui sera nettoyé.

2. **Point rapide en 3 temps** :
   - Où on en est globalement.
   - Ce qui a été fait **dans cette session** (depuis le dernier
     « Au revoir »/« On reprend »).
   - Les prochains points pour la prochaine session.

3. **Nettoyer la fenêtre de contexte** si besoin pour repartir propre la
   prochaine fois — proposer un `/compact` en Code, ou simplement s'assurer
   qu'aucune information importante ne reste uniquement « dans la tête » de la
   conversation.

---

## Pourquoi un fichier séparé (et plus la mémoire Cowork)

Ce rituel vivait avant dans la mémoire Cowork (`rituel-au-revoir`), invisible
en Claude Code. Le déplacer ici, comme [REPRISE.md](REPRISE.md), garantit qu'il
se déclenche et se déroule **pareil dans les deux contextes**.

Si ce rituel doit évoluer, modifier ce fichier (pas la mémoire Cowork) pour que
le changement profite aux deux environnements.
