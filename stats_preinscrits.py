#!/usr/bin/env python3
"""Stats des pré-inscrits (liste d'attente Neon).

Lit DATABASE_URL dans l'environnement — AUCUN secret en dur ici.
Usage :  DATABASE_URL="postgres://..." python3 stats_preinscrits.py

Sert au point quotidien automatique (routine) comme au point à la demande.
"""
import os
import sys
from collections import Counter

PG_URL = os.environ.get("DATABASE_URL")
if not PG_URL:
    sys.exit("DATABASE_URL manquant — exporte la chaîne de connexion Neon avant de lancer.")

import psycopg
from psycopg.rows import dict_row


def _rows():
    with psycopg.connect(PG_URL, row_factory=dict_row) as c:
        return c.execute(
            "SELECT email, prenom, profession, zone, niveau, a_partenaire, "
            "referred_by, source, created FROM waitlist ORDER BY created DESC"
        ).fetchall()


def _repartition(rows, champ, defaut="(non renseigné)"):
    c = Counter((r[champ] or defaut) for r in rows)
    return c.most_common()


def _bloc(titre, paires, total):
    lignes = [f"\n{titre}"]
    if not paires:
        lignes.append("  (aucun)")
    for k, n in paires:
        pct = f"{100*n/total:.0f}%" if total else "0%"
        lignes.append(f"  {n:>4}  {pct:>4}  {k}")
    return "\n".join(lignes)


def main():
    rows = _rows()
    total = len(rows)

    # Nouveaux récents (created est un timestamp ; on compare côté SQL pour fiabilité TZ)
    with psycopg.connect(PG_URL, row_factory=dict_row) as c:
        n24 = c.execute("SELECT COUNT(*) n FROM waitlist "
                        "WHERE created >= now() - interval '24 hours'").fetchone()["n"]
        n7 = c.execute("SELECT COUNT(*) n FROM waitlist "
                       "WHERE created >= now() - interval '7 days'").fetchone()["n"]

    parraines = sum(1 for r in rows if r["referred_by"])

    print("=" * 52)
    print("  LIGUE PADEL SANTÉ — PRÉ-INSCRITS")
    print("=" * 52)
    print(f"\nTOTAL : {total}")
    print(f"  +{n24} sur les dernières 24 h")
    print(f"  +{n7} sur les 7 derniers jours")
    print(f"  {parraines} via parrainage")

    print(_bloc("PAR SOURCE (?from=)", _repartition(rows, "source", "(direct)"), total))
    print(_bloc("PAR PROFESSION", _repartition(rows, "profession"), total))
    print(_bloc("PAR ZONE", _repartition(rows, "zone"), total))
    print(_bloc("PAR PRÉFÉRENCE DE JEU", _repartition(rows, "a_partenaire"), total))

    # Focus cardio (relais internes Johann/Samuel/Gabriel)
    cardio = [r for r in rows if (r["source"] or "") == "cardio"]
    print(f"\nFOCUS RELAIS CARDIO (?from=cardio) : {len(cardio)} inscrit(s)")


if __name__ == "__main__":
    main()
