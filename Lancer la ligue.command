#!/bin/bash
# Double-cliquez sur ce fichier pour lancer le prototype de la ligue.
# Une fenêtre Terminal s'ouvre, puis allez sur http://localhost:8000
cd "$(dirname "$0")"
echo "Démarrage du prototype de la Ligue de Padel des Médecins..."
echo "Ouvrez votre navigateur sur : http://localhost:8000"
echo "(Pour arrêter : fermez cette fenêtre ou appuyez sur Ctrl+C)"
echo
python3 app.py
