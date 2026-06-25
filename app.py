#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ligue de Padel des Médecins d'Île-de-France — PROTOTYPE LOCAL
=============================================================
Application web autonome, sans aucune dépendance à installer.
Utilise uniquement la bibliothèque standard de Python (http.server + sqlite3).

POUR LANCER :
    python3 app.py
puis ouvrir http://localhost:8000 dans le navigateur.

C'est une SIMULATION pour valider le fonctionnement (appariement suisse, cote
Elo, scores, classement). Ce n'est pas la version finale de production.
"""

import html
import http.server
import math
import os
import random
import re
import sqlite3
import urllib.parse

# Port et hôte : configurables par variables d'environnement (pour l'hébergement
# en ligne, type Render, qui impose le port via $PORT). En local : 8000.
PORT = int(os.environ.get("PORT", "8000"))
HOST = os.environ.get("HOST", "127.0.0.1")
DB_PATH = os.environ.get(
    "DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ligue.db"))
# URL publique de base (pour fabriquer les liens de parrainage partageables)
BASE_URL = os.environ.get("BASE_URL", "https://padel-med-league.fr")
# « Inscription avec Google » : actif seulement si un Client ID Google est fourni
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
# Lien du canal WhatsApp (diffusion anti-spam, abonnés anonymes). Affiché si défini ;
# surchargeable par variable d'environnement.
# ⚠️ Mettre le lien de la CHAÎNE (whatsapp.com/channel/…), pas d'un groupe : la copie
# du site/email parle de « canal » et le numéro des abonnés reste privé.
WHATSAPP_URL = os.environ.get(
    "WHATSAPP_URL", "https://whatsapp.com/channel/0029Vb8eeatEquiTLlgEGh2q")
# Mode pré-lancement : seule la landing (pré-inscription) est publique. La démo et
# l'admin ne sont accessibles qu'après déverrouillage via /apercu?cle=<APERCU_CODE>.
# Si APERCU_CODE n'est pas défini, démo + admin restent fermées à tout le monde.
APERCU_CODE = os.environ.get("APERCU_CODE")

# Emails (transactionnels + contacts) via Brevo. Tout est désactivé tant que
# BREVO_API_KEY n'est pas défini (repli gracieux : l'inscription marche sans email).
# L'expéditeur DOIT être un domaine/sender vérifié dans Brevo (ex. contact@…fr).
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
BREVO_LIST_ID = os.environ.get("BREVO_LIST_ID")  # liste de contacts (campagnes)
EMAIL_FROM = os.environ.get("EMAIL_FROM", "contact@padel-med-league.fr")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Ligue Padel Santé")
# Persistance : liste d'attente + parrainages stockés dans Neon (PostgreSQL) si
# DATABASE_URL est défini — sinon repli SQLite local.

# ---------------------------------------------------------------------------
# CONFIGURATION MÉTIER (reprend les décisions du PLAN.md)
# ---------------------------------------------------------------------------

NIVEAUX = {
    3: ("Débutant +", "Fondamentaux acquis, commence à jouer des matchs"),
    4: ("Intermédiaire", "Jeu régulier, premières stratégies, échanges tenus"),
    5: ("Intermédiaire +", "Technique approfondie, premiers tournois amateurs"),
    6: ("Avancé", "Peu de fautes directes, bonne défense, jeu offensif"),
    7: ("Avancé +", "Maîtrise technique et tactique complète"),
}

# Profession de santé (ouvert à tous les soignants, pas seulement les médecins)
PROFESSIONS = [
    "Médecin", "Chirurgien-dentiste", "Pharmacien", "Sage-femme",
    "Infirmier(ère)", "Masseur-kinésithérapeute", "Orthophoniste", "Orthoptiste",
    "Psychologue", "Pédicure-podologue", "Ergothérapeute", "Diététicien(ne)",
    "Manipulateur radio", "Ostéopathe", "Aide-soignant(e)", "Ambulancier",
    "Étudiant en santé", "Autre profession de santé",
]

# Mode / statut d'exercice (transversal à toutes les professions)
STATUTS = [
    "Libéral", "Hospitalier", "Salarié", "Interne", "Remplaçant",
    "Étudiant", "Retraité",
]

# Spécialité / domaine (surtout pertinent pour les médecins — optionnel)
SPECIALITES = [
    "—", "Cardiologie", "Médecine générale", "Anesthésie-réanimation", "Chirurgie",
    "Radiologie", "Pédiatrie", "Gynécologie", "Dermatologie", "Ophtalmologie",
    "Psychiatrie", "Urgences", "Médecine interne", "Néphrologie",
    "Pneumologie", "Gastro-entérologie", "Endocrinologie", "Rhumatologie",
    "Neurologie", "Oncologie", "Autre",
]

# Suggestions (champ libre) pour la structure d'exercice
EXEMPLES_STRUCTURES = [
    "Hôpital public (AP-HP)", "CHU", "Clinique privée", "Cabinet libéral",
    "Centre de santé", "ESPIC", "Médecine du travail", "Internat / CCA",
]

# Programme de parrainage : paliers de récompense (statut / priorité, sans coût)
REF_MILESTONES = [
    (1, "🎖️ Membre du Club des Fondateurs", "badge exclusif + mise en avant"),
    (3, "⭐ Accès prioritaire", "aux créneaux & avantages de nos clubs partenaires"),
    (5, "🏅 Statut Ambassadeur", "ton nom mis en avant sur notre Instagram"),
    (10, "👑 Capitaine de zone", "tu co-animes ta zone + un lot des clubs partenaires"),
]
# Image de partage (Open Graph) — hébergée sur le dépôt public GitHub
OG_IMAGE = ("https://raw.githubusercontent.com/NathanEB26/padel-med-league/"
            "main/visuels-instagram/01-annonce.png")

# Sondage liste d'attente : préférence de mode de jeu (stocké dans waitlist.a_partenaire)
PREF_OPTIONS = [
    "En équipe — j'ai déjà un binôme",
    "En solo (partenaires tournants)",
    "Peu importe / les deux",
]
# Regroupement pour l'affichage des résultats (3 buckets). On garde l'ancien libellé
# « j'en cherche un » dans le bucket Équipe pour rester compatible avec d'éventuelles
# réponses déjà enregistrées.
PREF_BUCKETS = [
    ("Équipe", (PREF_OPTIONS[0], "En équipe — j'en cherche un")),
    ("Solo", (PREF_OPTIONS[1],)),
    ("Peu importe", (PREF_OPTIONS[2],)),
]

# Quadrillage fin : 8 directions + Centre, placées sur une boussole.
ZONE_COORDS = {
    "Centre":     (0, 0),
    "Nord":       (0, 1),  "Sud":        (0, -1),
    "Est":        (1, 0),  "Ouest":      (-1, 0),
    "Nord-Est":   (1, 1),  "Sud-Est":    (1, -1),
    "Sud-Ouest":  (-1, -1), "Nord-Ouest": (-1, 1),
}
ZONES = list(ZONE_COORDS)
ZONES_INFO = {
    "Centre":     "Paris (75) intra-muros",
    "Nord":       "Val-d'Oise est (95) — Roissy, Sarcelles",
    "Nord-Est":   "Seine-Saint-Denis (93) — Casa Padel, 4Padel Marville",
    "Est":        "Seine-et-Marne (77) — 4Padel Vaires-Torcy",
    "Sud-Est":    "Val-de-Marne (94) — Padel Horizon (Sucy)",
    "Sud":        "Essonne (91) — ACE Padel Évry, Wissous, Massy",
    "Sud-Ouest":  "Yvelines sud (78) — Versailles, Les Pyramides",
    "Ouest":      "Hauts-de-Seine (92) — Boulogne, Nanterre",
    "Nord-Ouest": "Cergy-Pontoise (95) / Mantes (78)",
}

# Paramètres de l'appariement (système suisse) et de la cote Elo
K_ELO = 24                 # vitesse d'évolution de la cote
PEN_ZONE = 120             # pénalité de coût par unité de distance géographique
PEN_REMATCH = 800          # pénalité de coût par match déjà joué entre 2 équipes


def niveau_to_rating(niveau_equipe):
    """Convertit un niveau d'équipe (3-7) en cote Elo de départ."""
    return 1000 + (niveau_equipe - 3) * 100


def zone_distance(a, b):
    """Distance « à vol d'oiseau » entre 2 zones sur la boussole (0 à 2.83)."""
    ax, ay = ZONE_COORDS.get(a, (0, 0))
    bx, by = ZONE_COORDS.get(b, (0, 0))
    return math.hypot(ax - bx, ay - by)


def zone_from_cp(cp):
    """Détecte la zone à partir d'un code postal d'Île-de-France (approx., hors ligne)."""
    cp = (cp or "").strip()
    if len(cp) < 2 or not cp[:2].isdigit():
        return None
    dep, p3 = cp[:2], cp[:3]
    table = {"75": "Centre", "92": "Ouest", "93": "Nord-Est",
             "94": "Sud-Est", "91": "Sud", "77": "Est"}
    if dep in table:
        return table[dep]
    if dep == "95":
        return "Nord-Ouest" if p3 in {"950", "953", "954"} else "Nord"  # Cergy/Pontoise
    if dep == "78":
        return "Nord-Ouest" if p3 == "782" else "Sud-Ouest"            # Mantes
    return None


# ---------------------------------------------------------------------------
# BASE DE DONNÉES
# ---------------------------------------------------------------------------

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(reset=False):
    conn = db()
    if reset:
        conn.executescript("""
            DROP TABLE IF EXISTS scores;
            DROP TABLE IF EXISTS matchs_solo;
            DROP TABLE IF EXISTS journees_solo;
            DROP TABLE IF EXISTS matchs;
            DROP TABLE IF EXISTS journees;
            DROP TABLE IF EXISTS joueurs;
            DROP TABLE IF EXISTS equipes;
        """)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS equipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            zone TEXT NOT NULL,
            zone2 TEXT,
            niveau REAL NOT NULL,
            rating REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS joueurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            nom TEXT NOT NULL,
            email TEXT, telephone TEXT,
            profession TEXT, statut TEXT, specialite TEXT, structure TEXT,
            niveau INTEGER,
            rating REAL DEFAULT 1100,   -- cote Elo individuelle
            mode TEXT DEFAULT 'classique',  -- 'classique' (binôme fixe) ou 'solo' (tournant)
            zone TEXT, cp TEXT,
            equipe_id INTEGER REFERENCES equipes(id)   -- NULL = joueur libre
        );
        CREATE TABLE IF NOT EXISTS journees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS matchs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journee_id INTEGER NOT NULL REFERENCES journees(id),
            equipe_a INTEGER REFERENCES equipes(id),
            equipe_b INTEGER REFERENCES equipes(id),
            statut TEXT NOT NULL DEFAULT 'a_jouer',  -- a_jouer / valide / repos
            sets_a INTEGER, sets_b INTEGER,
            jeux_a INTEGER, jeux_b INTEGER,
            detail TEXT,
            vainqueur INTEGER
        );
        -- Mode tournant (Americano) : journées et matchs entre 4 joueurs solo
        CREATE TABLE IF NOT EXISTS journees_solo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS matchs_solo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journee_id INTEGER NOT NULL REFERENCES journees_solo(id),
            a1 INTEGER REFERENCES joueurs(id), a2 INTEGER REFERENCES joueurs(id),
            b1 INTEGER REFERENCES joueurs(id), b2 INTEGER REFERENCES joueurs(id),
            statut TEXT NOT NULL DEFAULT 'a_jouer',  -- a_jouer / valide / repos
            sets_a INTEGER, sets_b INTEGER, jeux_a INTEGER, jeux_b INTEGER,
            detail TEXT, vainqueur_side TEXT
        );
        -- Liste d'attente (pré-lancement) : conservée même quand on réinitialise la démo
        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            prenom TEXT, profession TEXT, zone TEXT, niveau INTEGER,
            a_partenaire TEXT,
            consent INTEGER DEFAULT 0,  -- consentement RGPD recueilli (1) ou non (0)
            source TEXT,                -- canal d'acquisition (?from=…, ex. "sihp")
            ref_code TEXT UNIQUE,       -- code de parrainage personnel
            referred_by TEXT,           -- code du parrain (si invité)
            created TEXT DEFAULT (datetime('now'))
        );
    """)
    # Migration : ajoute les colonnes manquantes aux bases déjà créées
    cols = [r[1] for r in conn.execute("PRAGMA table_info(waitlist)").fetchall()]
    if "consent" not in cols:
        conn.execute("ALTER TABLE waitlist ADD COLUMN consent INTEGER DEFAULT 0")
    if "source" not in cols:
        conn.execute("ALTER TABLE waitlist ADD COLUMN source TEXT")
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# LISTE D'ATTENTE & PARRAINAGE — persistance
# Si la variable d'environnement DATABASE_URL est définie (PostgreSQL, ex. Neon),
# la liste d'attente y est stockée durablement. Sinon, repli sur SQLite (local /
# démo, éphémère). Le reste de l'app (démo) reste sur SQLite.
# ---------------------------------------------------------------------------

PG_URL = os.environ.get("DATABASE_URL")
_pg_ready = False


def _pg():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(PG_URL, autocommit=True, row_factory=dict_row)


def _pg_ensure():
    global _pg_ready
    if _pg_ready:
        return
    with _pg() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS waitlist (
            id SERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL, prenom TEXT,
            profession TEXT, zone TEXT, niveau INTEGER, a_partenaire TEXT,
            ref_code TEXT UNIQUE, referred_by TEXT,
            created TIMESTAMP DEFAULT now())""")
        # Migration : colonnes ajoutées sur les tables déjà déployées
        c.execute("ALTER TABLE waitlist ADD COLUMN IF NOT EXISTS "
                  "consent BOOLEAN DEFAULT FALSE")
        c.execute("ALTER TABLE waitlist ADD COLUMN IF NOT EXISTS source TEXT")
    _pg_ready = True


def _new_code(existe):
    """Génère un code de parrainage unique. `existe(code)` -> bool."""
    import secrets
    alpha = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sans caractères ambigus
    while True:
        code = "".join(secrets.choice(alpha) for _ in range(6))
        if not existe(code):
            return code


def count_waitlist():
    if PG_URL:
        _pg_ensure()
        with _pg() as c:
            return c.execute("SELECT COUNT(*) AS n FROM waitlist").fetchone()["n"]
    conn = db()
    init_db()
    n = conn.execute("SELECT COUNT(*) c FROM waitlist").fetchone()["c"]
    conn.close()
    return n


def add_waitlist(email, prenom=None, profession=None, zone=None, niveau=None,
                 a_partenaire=None, referred_by=None, consent=False, source=None):
    """Ajoute un email à la liste d'attente. Renvoie (nouveau, ref_code).

    `consent` : True si l'utilisateur a explicitement coché la case RGPD.
    `source`  : canal d'acquisition (paramètre ?from=…, ex. "sihp").
    """
    email = email.strip().lower()
    referred_by = referred_by or None
    source = (source or None)
    if PG_URL:
        _pg_ensure()
        with _pg() as c:
            row = c.execute("SELECT ref_code FROM waitlist WHERE email=%s",
                            (email,)).fetchone()
            if row:
                return False, row["ref_code"]
            code = _new_code(lambda x: c.execute(
                "SELECT 1 FROM waitlist WHERE ref_code=%s", (x,)).fetchone())
            c.execute(
                "INSERT INTO waitlist(email,prenom,profession,zone,niveau,"
                "a_partenaire,consent,source,ref_code,referred_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (email, prenom, profession, zone, niveau, a_partenaire,
                 bool(consent), source, code, referred_by))
            return True, code
    conn = db()
    existant = conn.execute("SELECT ref_code FROM waitlist WHERE email=?",
                            (email,)).fetchone()
    if existant:
        conn.close()
        return False, existant["ref_code"]
    code = _new_code(lambda x: conn.execute(
        "SELECT 1 FROM waitlist WHERE ref_code=?", (x,)).fetchone())
    conn.execute(
        "INSERT INTO waitlist(email, prenom, profession, zone, niveau, a_partenaire, "
        "consent, source, ref_code, referred_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (email, prenom, profession, zone, niveau, a_partenaire,
         1 if consent else 0, source, code, referred_by))
    conn.commit()
    conn.close()
    return True, code


def waitlist_par_code(code):
    """Renvoie l'inscrit correspondant à un code de parrainage (ou None)."""
    if not code:
        return None
    code = code.strip().upper()
    if PG_URL:
        _pg_ensure()
        with _pg() as c:
            return c.execute("SELECT * FROM waitlist WHERE ref_code=%s",
                             (code,)).fetchone()
    conn = db()
    init_db()
    r = conn.execute("SELECT * FROM waitlist WHERE ref_code=?", (code,)).fetchone()
    conn.close()
    return r


def compte_filleuls(code):
    """Nombre de personnes inscrites grâce à ce code de parrainage."""
    if not code:
        return 0
    if PG_URL:
        _pg_ensure()
        with _pg() as c:
            return c.execute("SELECT COUNT(*) AS n FROM waitlist WHERE referred_by=%s",
                             (code,)).fetchone()["n"]
    conn = db()
    n = conn.execute("SELECT COUNT(*) c FROM waitlist WHERE referred_by=?",
                     (code,)).fetchone()["c"]
    conn.close()
    return n


def classement_parrains():
    """Parrains classés par nombre de filleuls (décroissant).
    Renvoie une liste de tuples (ref_code, prenom, nb_filleuls). Sert au rang
    personnel et au podium anonymisé (S11 viralité). N'expose PAS d'email."""
    sql = (
        "SELECT p.ref_code AS ref_code, p.prenom AS prenom, COUNT(f.email) AS n "
        "FROM waitlist f JOIN waitlist p ON p.ref_code = f.referred_by "
        "GROUP BY p.ref_code, p.prenom ORDER BY n DESC")
    if PG_URL:
        _pg_ensure()
        with _pg() as c:
            rows = c.execute(sql).fetchall()
            return [(r["ref_code"], r["prenom"], r["n"]) for r in rows]
    conn = db()
    init_db()
    rows = conn.execute(sql).fetchall()
    conn.close()
    return [(r["ref_code"], r["prenom"], r["n"]) for r in rows]


def rang_parrain(code):
    """Rang du parrain `code` parmi les parrains actifs (1 = meilleur).
    Renvoie (rang, total_parrains). (0, n) si le code n'a aucun filleul."""
    if not code:
        return (0, 0)
    code = code.strip().upper()
    classt = classement_parrains()
    total = len(classt)
    for i, (rc, _prenom, _n) in enumerate(classt, start=1):
        if rc == code:
            return (i, total)
    return (0, total)


def waitlist_all():
    """Toute la liste d'attente (pour l'admin), liste de dicts."""
    cols = ("email", "prenom", "profession", "zone", "a_partenaire", "source",
            "ref_code", "referred_by", "created")
    if PG_URL:
        _pg_ensure()
        with _pg() as c:
            return c.execute(
                "SELECT email,prenom,profession,zone,a_partenaire,source,ref_code,"
                "referred_by,created FROM waitlist ORDER BY created DESC").fetchall()
    conn = db()
    init_db()
    rows = conn.execute(
        "SELECT email,prenom,profession,zone,a_partenaire,source,ref_code,referred_by,"
        "created FROM waitlist ORDER BY created DESC").fetchall()
    conn.close()
    return [{k: r[k] for k in cols} for r in rows]


def waitlist_nb_parraines():
    if PG_URL:
        _pg_ensure()
        with _pg() as c:
            return c.execute("SELECT COUNT(*) AS n FROM waitlist "
                             "WHERE referred_by IS NOT NULL").fetchone()["n"]
    conn = db()
    init_db()
    n = conn.execute("SELECT COUNT(*) c FROM waitlist "
                     "WHERE referred_by IS NOT NULL").fetchone()["c"]
    conn.close()
    return n


def waitlist_delete(email):
    """Supprime une entrée de la liste d'attente (par email)."""
    email = (email or "").strip().lower()
    if not email:
        return
    if PG_URL:
        _pg_ensure()
        with _pg() as c:
            c.execute("DELETE FROM waitlist WHERE email=%s", (email,))
        return
    conn = db()
    init_db()
    conn.execute("DELETE FROM waitlist WHERE email=?", (email,))
    conn.commit()
    conn.close()


def waitlist_pref_counts():
    """Compte les votes du sondage (préférence de mode), par valeur brute."""
    if PG_URL:
        _pg_ensure()
        with _pg() as c:
            rows = c.execute("SELECT a_partenaire AS v, COUNT(*) AS n FROM waitlist "
                             "WHERE a_partenaire IS NOT NULL GROUP BY a_partenaire").fetchall()
            return {r["v"]: r["n"] for r in rows}
    conn = db()
    init_db()
    rows = conn.execute("SELECT a_partenaire v, COUNT(*) n FROM waitlist "
                        "WHERE a_partenaire IS NOT NULL GROUP BY a_partenaire").fetchall()
    conn.close()
    return {r["v"]: r["n"] for r in rows}


# ---------------------------------------------------------------------------
# EMAILS (Brevo) — transactionnel + synchro des contacts
# Tout est no-op si BREVO_API_KEY n'est pas défini (l'inscription marche sans).
# Aucune dépendance : appels HTTP via urllib (stdlib).
# ---------------------------------------------------------------------------

def _brevo_post(path, payload):
    import json
    import urllib.request
    req = urllib.request.Request(
        "https://api.brevo.com/v3" + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"api-key": BREVO_API_KEY, "content-type": "application/json",
                 "accept": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status


def envoyer_email(to, sujet, html, nom=None):
    """Envoie un email transactionnel via Brevo. Silencieux si non configuré."""
    if not (BREVO_API_KEY and to):
        return
    dest = {"email": to}
    if nom:
        dest["name"] = nom
    payload = {"sender": {"email": EMAIL_FROM, "name": EMAIL_FROM_NAME},
               "to": [dest], "subject": sujet, "htmlContent": html}
    try:
        _brevo_post("/smtp/email", payload)
    except Exception:
        pass  # ne jamais casser le flux d'inscription si l'email échoue


def brevo_ajouter_contact(email, prenom=None):
    """Crée/maj le contact dans Brevo (pour les campagnes). Silencieux si non configuré."""
    if not (BREVO_API_KEY and email):
        return
    payload = {"email": email, "updateEnabled": True}
    if prenom:
        payload["attributes"] = {"PRENOM": prenom}
    if BREVO_LIST_ID:
        try:
            payload["listIds"] = [int(BREVO_LIST_ID)]
        except (TypeError, ValueError):
            pass
    try:
        _brevo_post("/contacts", payload)
    except Exception:
        pass


def email_confirmation_html(prenom, ref_code):
    """HTML de l'email de confirmation d'inscription (clair, délivrable)."""
    bonjour = f"Bonjour {e(prenom)}," if prenom else "Bonjour,"
    lien = f"{BASE_URL}/?ref={e(ref_code)}" if ref_code else BASE_URL
    # Canal WhatsApp = moyen le plus fiable d'être prévenu (anti-spam). Affiché si défini.
    whatsapp_phrase = (" — ou mieux, suis notre canal WhatsApp 👇" if WHATSAPP_URL
                       else "")
    whatsapp_btn = (
        f'<a href="{e(WHATSAPP_URL)}" style="display:inline-block;background:#25D366;'
        f'color:#06210f;font-weight:800;text-decoration:none;padding:11px 18px;'
        f'border-radius:8px;font-size:14px">💬 Suivre le canal WhatsApp</a>'
    ) if WHATSAPP_URL else ""
    return f"""\
<div style="background:#f4f6f8;padding:24px 0;font-family:Helvetica,Arial,sans-serif">
  <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:14px;
       overflow:hidden;border:1px solid #e3e8ee">
    <div style="background:#070b10;padding:22px 28px">
      <span style="color:#ffffff;font-weight:900;font-style:italic;font-size:18px">
      LIGUE PADEL SANTÉ</span>
      <span style="color:#c6ff00;font-weight:800;font-size:11px;letter-spacing:3px;
       display:block;margin-top:4px">ÎLE-DE-FRANCE</span>
    </div>
    <div style="padding:28px">
      <p style="font-size:16px;color:#0b1118;margin:0 0 14px">{bonjour}</p>
      <h1 style="font-size:22px;color:#0b1118;margin:0 0 12px">
      Tu es bien sur la liste d'attente 🎾</h1>
      <p style="font-size:15px;color:#3a4654;line-height:1.6;margin:0 0 16px">
      Merci de rejoindre la première ligue de padel des soignants d'Île-de-France !
      On te préviendra <strong>dès l'ouverture</strong> (coup d'envoi de la Saison 1 le
      <strong>1ᵉʳ septembre 2026</strong>), et tu seras <strong>prioritaire pour le Club
      des Fondateurs</strong> (50 premières équipes).</p>
      <p style="font-size:15px;color:#3a4654;line-height:1.6;margin:0 0 8px">
      <strong>Fais grimper la ligue :</strong> invite un·e collègue ou ton binôme avec
      ton lien perso 👇</p>
      <p style="margin:0 0 22px">
        <a href="{lien}" style="display:inline-block;background:#c6ff00;color:#06120a;
        font-weight:800;text-decoration:none;padding:12px 20px;border-radius:8px;
        font-size:14px">Partager mon lien d'invitation →</a></p>
      <div style="background:#eafaf0;border:1px solid #bfe9cf;border-radius:10px;
           padding:16px 18px;margin:0 0 20px">
        <p style="font-size:14px;color:#0b1118;line-height:1.6;margin:0 0 4px">
        <strong>📌 Pour être sûr·e de ne rien rater :</strong></p>
        <p style="font-size:14px;color:#3a4654;line-height:1.6;margin:0 0 12px">
        ajoute <strong>{EMAIL_FROM}</strong> à tes contacts (sinon nos prochains emails
        risquent les spams ou l'onglet Promotions){whatsapp_phrase}.</p>
        {whatsapp_btn}</div>
      <p style="font-size:13px;color:#8595a6;line-height:1.6;margin:0">
      Tu reçois cet email car tu t'es inscrit·e sur padel-med-league.fr. Pour te
      désinscrire ou toute question : <a href="mailto:{EMAIL_FROM}"
      style="color:#6b7a8c">{EMAIL_FROM}</a>.</p>
    </div>
  </div>
</div>"""


def post_inscription_emails(email, prenom, ref_code):
    """Effets de bord post-inscription : email de confirmation + contact Brevo.
    Conçu pour tourner dans un thread (fire-and-forget) afin de ne pas ralentir
    la redirection de l'utilisateur."""
    envoyer_email(email, "Bienvenue dans la Ligue Padel Santé 🎾",
                  email_confirmation_html(prenom, ref_code), nom=prenom)
    brevo_ajouter_contact(email, prenom)


# ---------------------------------------------------------------------------
# SEED — données de démonstration
# ---------------------------------------------------------------------------

SEED_EQUIPES = [
    # (nom, zone, [(joueur, profession, statut, specialite, structure, niveau) x2])
    ("Les Coronaires", "Centre", [
        ("Dr A. Lefort", "Médecin", "Libéral", "Cardiologie", "Cabinet libéral Paris 8", 6),
        ("Dr S. Mercier", "Médecin", "Hospitalier", "Cardiologie", "Hôpital Pitié-Salpêtrière", 5)]),
    ("Smash Réa", "Nord-Est", [
        ("Dr K. Benali", "Médecin", "Hospitalier", "Anesthésie-réanimation", "Hôpital Avicenne (Bobigny)", 7),
        ("Dr P. Aubry", "Médecin", "Hospitalier", "Anesthésie-réanimation", "Hôpital Avicenne (Bobigny)", 6)]),
    ("Kiné Vibora", "Sud", [
        ("M. M. Da Silva", "Masseur-kinésithérapeute", "Libéral", "—", "Cabinet de kiné Massy", 4),
        ("Mme L. Garnier", "Masseur-kinésithérapeute", "Libéral", "—", "Cabinet de kiné Massy", 4)]),
    ("Les Perfusions", "Est", [
        ("M. T. Hadji", "Infirmier(ère)", "Hospitalier", "Urgences", "CH de Meaux", 5),
        ("Mme R. Colin", "Infirmier(ère)", "Hospitalier", "Urgences", "CH de Meaux", 5)]),
    ("Les Scanners", "Ouest", [
        ("Dr E. Faure", "Médecin", "Libéral", "Radiologie", "Centre d'imagerie Boulogne", 6),
        ("M. N. Petit", "Manipulateur radio", "Salarié", "Radiologie", "Centre d'imagerie Boulogne", 6)]),
    ("Padel Pédia", "Centre", [
        ("Dr C. Roy", "Médecin", "Hospitalier", "Pédiatrie", "Hôpital Necker", 4),
        ("Dr V. Lambert", "Médecin", "Hospitalier", "Pédiatrie", "Hôpital Necker", 5)]),
    ("Net & Sutures", "Nord-Est", [
        ("Dr O. Marchand", "Médecin", "Hospitalier", "Chirurgie", "Hôpital Delafontaine (St-Denis)", 5),
        ("Dr F. Girard", "Chirurgien-dentiste", "Libéral", "—", "Cabinet dentaire Saint-Denis", 4)]),
    ("Les Néphrons", "Sud", [
        ("Dr H. Morel", "Médecin", "Libéral", "Néphrologie", "Clinique privée Évry", 6),
        ("Dr A. Texier", "Médecin", "Hospitalier", "Néphrologie", "CHSF Corbeil", 7)]),
    ("Derm'Smash", "Sud-Est", [
        ("Dr J. Bonnet", "Médecin", "Libéral", "Dermatologie", "Cabinet libéral Créteil", 3),
        ("M. Y. Rousseau", "Pharmacien", "Libéral", "—", "Pharmacie Vincennes", 4)]),
    ("Vibora Vision", "Sud-Ouest", [
        ("Dr B. Leroy", "Médecin", "Libéral", "Ophtalmologie", "Cabinet Versailles", 5),
        ("Mme D. Henry", "Orthoptiste", "Libéral", "—", "Cabinet Versailles", 5)]),
    ("Les Synapses", "Nord-Ouest", [
        ("Dr G. Picard", "Médecin", "Hospitalier", "Neurologie", "Hôpital de Cergy-Pontoise", 6),
        ("Mme I. Noël", "Psychologue", "Salarié", "—", "Hôpital de Cergy-Pontoise", 5)]),
    ("Sages & Smash", "Nord", [
        ("Mme W. Sanchez", "Sage-femme", "Hospitalier", "Gynécologie", "CH de Gonesse", 4),
        ("Mme Z. Fontaine", "Sage-femme", "Hospitalier", "Gynécologie", "CH de Gonesse", 3)]),
]


def niveau_equipe(n1, n2):
    """Moyenne tirée vers le plus fort : 0.4*min + 0.6*max."""
    return round(0.4 * min(n1, n2) + 0.6 * max(n1, n2), 2)


def slugify(nom):
    s = nom.lower().replace("dr ", "").replace("dr. ", "").strip()
    s = re.sub(r"[^a-z0-9]+", ".", s).strip(".")
    return s or "joueur"


def username_unique(conn, nom):
    base = slugify(nom)
    un, i = base, 2
    while conn.execute("SELECT 1 FROM joueurs WHERE username=?", (un,)).fetchone():
        un, i = f"{base}{i}", i + 1
    return un


def find_joueur(conn, cle):
    """Recherche un joueur par pseudo OU email (exact, insensible à la casse)."""
    cle = (cle or "").strip().lower()
    if not cle:
        return None
    return conn.execute(
        "SELECT * FROM joueurs WHERE lower(username)=? OR lower(email)=?",
        (cle, cle)).fetchone()


def creer_joueur(conn, nom, **kw):
    un = kw.get("username") or username_unique(conn, nom)
    if conn.execute("SELECT 1 FROM joueurs WHERE username=?", (un,)).fetchone():
        un = username_unique(conn, un)
    niveau = kw.get("niveau")
    rating = niveau_to_rating(niveau) if niveau else 1100
    cur = conn.execute(
        "INSERT INTO joueurs(username, nom, email, telephone, profession, statut, "
        "specialite, structure, niveau, rating, mode, zone, cp, equipe_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
        (un, nom, kw.get("email"), kw.get("telephone"), kw.get("profession"),
         kw.get("statut"), kw.get("specialite"), kw.get("structure"),
         niveau, rating, kw.get("mode", "classique"), kw.get("zone"), kw.get("cp")))
    return cur.lastrowid, un


def former_equipe(conn, nom_equipe, jid1, jid2, zone=None, zone2=None):
    """Crée une équipe à partir de 2 joueurs libres et les y rattache."""
    j1 = conn.execute("SELECT * FROM joueurs WHERE id=?", (jid1,)).fetchone()
    j2 = conn.execute("SELECT * FROM joueurs WHERE id=?", (jid2,)).fetchone()
    nv = niveau_equipe(j1["niveau"], j2["niveau"])
    z = zone or j1["zone"] or "Centre"
    eid = conn.execute(
        "INSERT INTO equipes(nom, zone, zone2, niveau, rating) VALUES (?,?,?,?,?)",
        (nom_equipe, z, zone2, nv, niveau_to_rating(nv))).lastrowid
    conn.execute("UPDATE joueurs SET equipe_id=? WHERE id IN (?,?)", (eid, jid1, jid2))
    return eid


SEED_SOLO = [
    # (nom, profession, statut, specialite, structure, niveau, zone)
    ("Dr Inès Moreau", "Médecin", "Hospitalier", "Cardiologie", "HEGP", 6, "Centre"),
    ("Mme Sarah Lopez", "Infirmier(ère)", "Hospitalier", "—", "Hôpital Cochin", 5, "Centre"),
    ("M. Karim Sow", "Masseur-kinésithérapeute", "Libéral", "—", "Cabinet Montreuil", 4, "Nord-Est"),
    ("Dr Hugo Berger", "Médecin", "Interne", "Urgences", "CHU Bicêtre", 5, "Sud"),
    ("Mme Chloé Marchetti", "Sage-femme", "Hospitalier", "Gynécologie", "Maternité Port-Royal", 4, "Centre"),
    ("Dr Antoine Rey", "Chirurgien-dentiste", "Libéral", "—", "Cabinet Neuilly", 6, "Ouest"),
    ("Mme Léa Dubois", "Orthophoniste", "Libéral", "—", "Cabinet Vincennes", 3, "Sud-Est"),
    ("Dr Yanis Cohen", "Médecin", "Libéral", "Dermatologie", "Cabinet Paris 16", 7, "Ouest"),
    ("M. Paul Girard", "Pharmacien", "Libéral", "—", "Pharmacie Créteil", 5, "Sud-Est"),
    ("Dr Nadia Haddad", "Médecin", "Hospitalier", "Pédiatrie", "Hôpital Trousseau", 6, "Est"),
    ("Mme Emma Roux", "Psychologue", "Salarié", "—", "CMP Nanterre", 4, "Ouest"),
    ("M. Lucas Petit", "Étudiant en santé", "Étudiant", "—", "Université Paris Cité", 5, "Centre"),
]


def seed():
    init_db(reset=True)
    conn = db()
    for nom, zone, joueurs in SEED_EQUIPES:
        pids = []
        for (jn, profession, statut, spe, structure, niv) in joueurs:
            pid, un = creer_joueur(conn, jn, profession=profession, statut=statut,
                                   specialite=spe, structure=structure, niveau=niv,
                                   zone=zone, email=f"{slugify(jn)}@demo.fr")
            pids.append(pid)
        former_equipe(conn, nom, pids[0], pids[1], zone=zone)
    conn.commit()
    conn.close()
    # Génère la journée 1 et joue quelques matchs pour peupler le classement
    generer_journee()
    conn = db()
    matchs = conn.execute(
        "SELECT id, equipe_a, equipe_b FROM matchs WHERE statut='a_jouer'").fetchall()
    conn.close()
    random.seed(42)
    scores_demo = [("6-3", "6-4"), ("6-2", "4-6", "7-5"),
                   ("3-6", "6-4", "6-2"), ("6-1", "6-3")]
    for i, m in enumerate(matchs):
        if i % 2 == 0:  # on ne joue qu'un match sur deux pour montrer les 2 états
            enregistrer_score(m["id"], random.choice(scores_demo))

    # Mode tournant (Americano) : joueurs solo + une journée jouée
    conn = db()
    for (jn, prof, stat, spe, struct, niv, zone) in SEED_SOLO:
        creer_joueur(conn, jn, profession=prof, statut=stat, specialite=spe,
                     structure=struct, niveau=niv, zone=zone, mode="solo",
                     email=f"{slugify(jn)}@demo.fr")
    conn.commit()
    conn.close()
    generer_journee_solo()
    conn = db()
    ms = conn.execute("SELECT id FROM matchs_solo WHERE statut='a_jouer'").fetchall()
    conn.close()
    for i, m in enumerate(ms):
        if i % 2 == 0:
            enregistrer_score_solo(m["id"], random.choice(scores_demo))


# ---------------------------------------------------------------------------
# CLASSEMENT
# ---------------------------------------------------------------------------

def points_match(sets_pour, sets_contre):
    if sets_pour == 2 and sets_contre == 0:
        return 3
    if sets_pour == 2 and sets_contre == 1:
        return 2
    if sets_pour == 1 and sets_contre == 2:
        return 1
    return 0


def classement():
    conn = db()
    equipes = conn.execute("SELECT * FROM equipes").fetchall()
    stats = {e["id"]: {"equipe": e, "j": 0, "v": 0, "pts": 0,
                       "sg": 0, "sp": 0, "jg": 0, "jp": 0} for e in equipes}
    matchs = conn.execute("SELECT * FROM matchs WHERE statut='valide'").fetchall()
    conn.close()
    for m in matchs:
        for (moi, adv, sp, sc, jp_, jc) in (
            (m["equipe_a"], m["equipe_b"], m["sets_a"], m["sets_b"], m["jeux_a"], m["jeux_b"]),
            (m["equipe_b"], m["equipe_a"], m["sets_b"], m["sets_a"], m["jeux_b"], m["jeux_a"]),
        ):
            st = stats[moi]
            st["j"] += 1
            st["pts"] += points_match(sp, sc)
            st["sg"] += sp; st["sp"] += sc
            st["jg"] += jp_; st["jp"] += jc
            if sp > sc:
                st["v"] += 1
    table = list(stats.values())
    table.sort(key=lambda s: (s["pts"], s["sg"] - s["sp"], s["jg"] - s["jp"]),
               reverse=True)
    return table


def stats_joueurs():
    """Agrège les résultats au niveau de chaque JOUEUR (les 2 d'une équipe
    partagent le résultat du match). Base des classements individuels et de groupe."""
    conn = db()
    joueurs = {j["id"]: dict(joueur=j, j=0, v=0, pts=0)
               for j in conn.execute(
                   "SELECT * FROM joueurs WHERE equipe_id IS NOT NULL OR mode='solo'")}

    def crediter(pid, sp, sc):
        if pid in joueurs:
            st = joueurs[pid]
            st["j"] += 1
            st["pts"] += points_match(sp, sc)
            if sp > sc:
                st["v"] += 1

    membres = {}  # equipe_id -> [player_id]
    for j in conn.execute("SELECT id, equipe_id FROM joueurs WHERE equipe_id IS NOT NULL"):
        membres.setdefault(j["equipe_id"], []).append(j["id"])
    for m in conn.execute("SELECT * FROM matchs WHERE statut='valide'"):
        for (eq, sp, sc) in ((m["equipe_a"], m["sets_a"], m["sets_b"]),
                             (m["equipe_b"], m["sets_b"], m["sets_a"])):
            for pid in membres.get(eq, []):
                crediter(pid, sp, sc)
    # matchs tournants (mode solo)
    for m in conn.execute("SELECT * FROM matchs_solo WHERE statut='valide'"):
        for (joueurs_cote, sp, sc) in (([m["a1"], m["a2"]], m["sets_a"], m["sets_b"]),
                                       ([m["b1"], m["b2"]], m["sets_b"], m["sets_a"])):
            for pid in joueurs_cote:
                crediter(pid, sp, sc)
    conn.close()
    return joueurs


def classement_joueurs():
    table = list(stats_joueurs().values())
    table.sort(key=lambda s: (s["pts"], s["joueur"]["rating"]), reverse=True)
    return table


def classement_par(attribut):
    """Classement de groupe (profession / specialite / structure / zone),
    par attribution individuelle. Renvoie une liste triée par points par tête."""
    groupes = {}
    for st in stats_joueurs().values():
        if st["j"] == 0:
            continue  # n'a pas encore joué
        cle = st["joueur"][attribut]
        if not cle or cle == "—":
            continue
        g = groupes.setdefault(cle, dict(nom=cle, joueurs=0, j=0, v=0, pts=0, somme_cote=0))
        g["joueurs"] += 1
        g["j"] += st["j"]
        g["v"] += st["v"]
        g["pts"] += st["pts"]
        g["somme_cote"] += st["joueur"]["rating"]
    table = list(groupes.values())
    for g in table:
        g["pts_par_tete"] = round(g["pts"] / g["joueurs"], 2) if g["joueurs"] else 0
        g["cote_moy"] = round(g["somme_cote"] / g["joueurs"]) if g["joueurs"] else 0
    table.sort(key=lambda g: (g["pts_par_tete"], g["cote_moy"]), reverse=True)
    return table


# ---------------------------------------------------------------------------
# APPARIEMENT SUISSE + COTE ELO
# ---------------------------------------------------------------------------

def nb_rencontres(conn, a, b):
    r = conn.execute(
        "SELECT COUNT(*) c FROM matchs WHERE statut!='repos' AND "
        "((equipe_a=? AND equipe_b=?) OR (equipe_a=? AND equipe_b=?))",
        (a, b, b, a)).fetchone()
    return r["c"]


def deja_repos(conn, eid):
    r = conn.execute(
        "SELECT COUNT(*) c FROM matchs WHERE statut='repos' AND equipe_a=?",
        (eid,)).fetchone()
    return r["c"]


def cout(conn, e1, e2):
    """Coût d'un appariement : écart de niveau + distance géo + anti-rematch."""
    c = abs(e1["rating"] - e2["rating"])
    c += PEN_ZONE * zone_distance(e1["zone"], e2["zone"])
    c += PEN_REMATCH * nb_rencontres(conn, e1["id"], e2["id"])
    return c


def generer_journee():
    """Crée la prochaine journée par appariement suisse (glouton, coût minimal)."""
    conn = db()
    equipes = {e["id"]: e for e in conn.execute("SELECT * FROM equipes").fetchall()}
    if len(equipes) < 2:
        conn.close()
        return None

    # Ordre du classement (parcours suisse du haut vers le bas)
    ordre_ids = [s["equipe"]["id"] for s in classement()]
    restants = list(ordre_ids)

    bye = None
    if len(restants) % 2 == 1:
        # Repos pour l'équipe la moins bien classée qui n'a pas encore eu de repos
        for eid in reversed(restants):
            if deja_repos(conn, eid) == 0:
                bye = eid
                break
        if bye is None:
            bye = restants[-1]
        restants.remove(bye)

    paires = []
    en_attente = list(restants)
    while en_attente:
        t = en_attente.pop(0)
        meilleur, meilleur_cout = None, float("inf")
        for u in en_attente:
            c = cout(conn, equipes[t], equipes[u])
            if c < meilleur_cout:
                meilleur_cout, meilleur = c, u
        if meilleur is not None:
            paires.append((t, meilleur))
            en_attente.remove(meilleur)

    numero = (conn.execute("SELECT COALESCE(MAX(numero),0) m FROM journees")
              .fetchone()["m"]) + 1
    jid = conn.execute("INSERT INTO journees(numero) VALUES (?)", (numero,)).lastrowid
    for a, b in paires:
        conn.execute(
            "INSERT INTO matchs(journee_id, equipe_a, equipe_b, statut) "
            "VALUES (?,?,?, 'a_jouer')", (jid, a, b))
    if bye is not None:
        conn.execute(
            "INSERT INTO matchs(journee_id, equipe_a, equipe_b, statut) "
            "VALUES (?,?,NULL, 'repos')", (jid, bye))
    conn.commit()
    conn.close()
    return numero


def maj_elo(conn, a, b, score_a):
    """Met à jour la cote Elo des 2 équipes. score_a : 1 victoire A, 0 victoire B."""
    ea = conn.execute("SELECT rating FROM equipes WHERE id=?", (a,)).fetchone()["rating"]
    eb = conn.execute("SELECT rating FROM equipes WHERE id=?", (b,)).fetchone()["rating"]
    att_a = 1 / (1 + 10 ** ((eb - ea) / 400))
    na = ea + K_ELO * (score_a - att_a)
    nb = eb + K_ELO * ((1 - score_a) - (1 - att_a))
    conn.execute("UPDATE equipes SET rating=? WHERE id=?", (round(na, 1), a))
    conn.execute("UPDATE equipes SET rating=? WHERE id=?", (round(nb, 1), b))


def maj_elo_joueurs(conn, a, b, score_a):
    """Cote Elo individuelle (2v2) : chaque joueur d'une paire prend le même delta,
    calculé sur la moyenne des cotes de chaque paire."""
    ja = conn.execute("SELECT id, rating FROM joueurs WHERE equipe_id=?", (a,)).fetchall()
    jb = conn.execute("SELECT id, rating FROM joueurs WHERE equipe_id=?", (b,)).fetchall()
    if not ja or not jb:
        return
    moy_a = sum(j["rating"] for j in ja) / len(ja)
    moy_b = sum(j["rating"] for j in jb) / len(jb)
    att_a = 1 / (1 + 10 ** ((moy_b - moy_a) / 400))
    delta = K_ELO * (score_a - att_a)
    for j in ja:
        conn.execute("UPDATE joueurs SET rating=? WHERE id=?",
                     (round(j["rating"] + delta, 1), j["id"]))
    for j in jb:
        conn.execute("UPDATE joueurs SET rating=? WHERE id=?",
                     (round(j["rating"] - delta, 1), j["id"]))


def parse_sets(sets):
    """sets : liste de chaînes '6-3'. Renvoie (sets_a, sets_b, jeux_a, jeux_b)."""
    sa = sb = ja = jb = 0
    for s in sets:
        ga, gb = (int(x) for x in s.split("-"))
        ja += ga; jb += gb
        if ga > gb:
            sa += 1
        else:
            sb += 1
    return sa, sb, ja, jb


def enregistrer_score(match_id, sets):
    conn = db()
    m = conn.execute("SELECT * FROM matchs WHERE id=?", (match_id,)).fetchone()
    if not m or m["statut"] == 'repos':
        conn.close()
        return False
    sa, sb, ja, jb = parse_sets(sets)
    vainqueur = m["equipe_a"] if sa > sb else m["equipe_b"]
    detail = " / ".join(sets)
    conn.execute(
        "UPDATE matchs SET statut='valide', sets_a=?, sets_b=?, jeux_a=?, jeux_b=?, "
        "detail=?, vainqueur=? WHERE id=?",
        (sa, sb, ja, jb, detail, vainqueur, match_id))
    maj_elo(conn, m["equipe_a"], m["equipe_b"], 1 if sa > sb else 0)
    maj_elo_joueurs(conn, m["equipe_a"], m["equipe_b"], 1 if sa > sb else 0)
    conn.commit()
    conn.close()
    return True


# ---------------------------------------------------------------------------
# MODE TOURNANT (AMERICANO) — partenaires & adversaires changeants
# ---------------------------------------------------------------------------

PEN_PARTENAIRE = 500  # pénalité si deux joueurs ont déjà été partenaires


def nb_partenaires(conn, a, b):
    """Combien de fois a et b ont déjà été partenaires (même côté) en tournant."""
    return conn.execute(
        "SELECT COUNT(*) c FROM matchs_solo WHERE statut!='repos' AND "
        "((a1=? AND a2=?) OR (a1=? AND a2=?) OR (b1=? AND b2=?) OR (b1=? AND b2=?))",
        (a, b, b, a, a, b, b, a)).fetchone()["c"]


def deja_repos_solo(conn, pid):
    return conn.execute(
        "SELECT COUNT(*) c FROM matchs_solo WHERE statut='repos' AND a1=?",
        (pid,)).fetchone()["c"]


def maj_elo_solo(conn, A, B, score_a):
    """Cote individuelle pour un match tournant : A et B = listes de 2 joueurs."""
    ra = {i: conn.execute("SELECT rating FROM joueurs WHERE id=?", (i,)).fetchone()["rating"] for i in A + B}
    moy_a = (ra[A[0]] + ra[A[1]]) / 2
    moy_b = (ra[B[0]] + ra[B[1]]) / 2
    att_a = 1 / (1 + 10 ** ((moy_b - moy_a) / 400))
    delta = K_ELO * (score_a - att_a)
    for i in A:
        conn.execute("UPDATE joueurs SET rating=? WHERE id=?", (round(ra[i] + delta, 1), i))
    for i in B:
        conn.execute("UPDATE joueurs SET rating=? WHERE id=?", (round(ra[i] - delta, 1), i))


def generer_journee_solo():
    """Crée une journée tournante (Americano) : courts de 4 par niveau, paires
    équilibrées et renouvelées (anti même partenaire)."""
    conn = db()
    players = conn.execute(
        "SELECT id, rating FROM joueurs WHERE mode='solo'").fetchall()
    if len(players) < 4:
        conn.close()
        return None
    rating = {p["id"]: p["rating"] for p in players}
    ids = sorted(rating, key=lambda i: rating[i], reverse=True)

    # Journée de repos pour le reste (n % 4) : priorité à ceux qui ont le moins reposé
    reste = len(ids) % 4
    byes = sorted(ids, key=lambda i: (deja_repos_solo(conn, i), rating[i]))[:reste]
    restants = [i for i in ids if i not in byes]
    restants.sort(key=lambda i: rating[i], reverse=True)

    numero = (conn.execute("SELECT COALESCE(MAX(numero),0) m FROM journees_solo")
              .fetchone()["m"]) + 1
    jid = conn.execute("INSERT INTO journees_solo(numero) VALUES (?)", (numero,)).lastrowid

    for k in range(0, len(restants), 4):
        q = restants[k:k + 4]
        splits = [((q[0], q[3]), (q[1], q[2])),
                  ((q[0], q[2]), (q[1], q[3])),
                  ((q[0], q[1]), (q[2], q[3]))]
        best, best_cout = None, float("inf")
        for (pa, pb) in splits:
            desequilibre = abs((rating[pa[0]] + rating[pa[1]]) - (rating[pb[0]] + rating[pb[1]]))
            repeats = nb_partenaires(conn, *pa) + nb_partenaires(conn, *pb)
            c = desequilibre + PEN_PARTENAIRE * repeats
            if c < best_cout:
                best_cout, best = c, (pa, pb)
        (a1, a2), (b1, b2) = best
        conn.execute(
            "INSERT INTO matchs_solo(journee_id, a1, a2, b1, b2, statut) "
            "VALUES (?,?,?,?,?, 'a_jouer')", (jid, a1, a2, b1, b2))

    for pid in byes:
        conn.execute(
            "INSERT INTO matchs_solo(journee_id, a1, statut) VALUES (?,?, 'repos')",
            (jid, pid))
    conn.commit()
    conn.close()
    return numero


def enregistrer_score_solo(match_id, sets):
    conn = db()
    m = conn.execute("SELECT * FROM matchs_solo WHERE id=?", (match_id,)).fetchone()
    if not m or m["statut"] == "repos":
        conn.close()
        return False
    sa, sb, ja, jb = parse_sets(sets)
    side = "A" if sa > sb else "B"
    conn.execute(
        "UPDATE matchs_solo SET statut='valide', sets_a=?, sets_b=?, jeux_a=?, "
        "jeux_b=?, detail=?, vainqueur_side=? WHERE id=?",
        (sa, sb, ja, jb, " / ".join(sets), side, match_id))
    maj_elo_solo(conn, [m["a1"], m["a2"]], [m["b1"], m["b2"]], 1 if sa > sb else 0)
    conn.commit()
    conn.close()
    return True


# ---------------------------------------------------------------------------
# QUESTIONNAIRE D'ESTIMATION (Porte D)
# ---------------------------------------------------------------------------

QUESTIONS = [
    ("anciennete", "Depuis combien de temps jouez-vous ?",
     [("< 6 mois", 0), ("6 à 24 mois", 1), ("> 2 ans", 2)]),
    ("freq", "À quelle fréquence jouez-vous ?",
     [("Occasionnel", 0), ("1×/semaine", 1), ("2×/semaine ou +", 2)]),
    ("vitre", "Maîtrisez-vous la sortie de vitre (défense au mur) ?",
     [("Non", 0), ("Parfois", 1), ("Oui", 2)]),
    ("tete", "Coups au-dessus de la tête (bandeja / víbora) ?",
     [("Aucun", 0), ("La bandeja", 1), ("Les deux", 2)]),
    ("tournoi", "Participez-vous à des tournois ?",
     [("Jamais", 0), ("P25-P100", 1), ("P250 et +", 2)]),
]


def estimer_niveau(scores):
    total = sum(scores)  # 0 à 10
    return min(7, max(3, 3 + round(total / 10 * 4)))


# ===========================================================================
# RENDU HTML
# ===========================================================================

def e(s):
    return html.escape(str(s if s is not None else ""))


CSS = """
:root{--bg:#070b10;--bg2:#0c1219;--panel:#111a24;--panel2:#172230;
--line:#22303f;--txt:#eef3f6;--muted:#8595a6;
--lime:#c6ff00;--lime2:#9fe000;--mag:#ff2f7a;--cyan:#1ad1ff;--gold:#ffce3a;}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;color:var(--txt);line-height:1.5;-webkit-font-smoothing:antialiased;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
background:radial-gradient(1200px 600px at 82% -12%,rgba(198,255,0,.09),transparent 60%),
radial-gradient(1000px 520px at -12% 8%,rgba(255,47,122,.08),transparent 55%),var(--bg);}
header{position:sticky;top:0;z-index:50;background:rgba(7,11,16,.86);
backdrop-filter:blur(10px);border-bottom:2px solid var(--lime);
display:flex;align-items:center;gap:16px;padding:12px 22px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:11px;font-weight:900;font-style:italic;
text-transform:uppercase;letter-spacing:.4px;font-size:18px;line-height:1}
.brand .ball{width:30px;height:30px;border-radius:50%;background:var(--lime);
display:inline-flex;align-items:center;justify-content:center;font-size:16px;
box-shadow:0 0 18px rgba(198,255,0,.6)}
.brand small{display:block;font-size:9px;font-weight:800;font-style:normal;
letter-spacing:3px;color:var(--lime);margin-top:3px}
nav{margin-left:auto;display:flex;gap:4px;flex-wrap:wrap}
nav a{color:var(--muted);text-decoration:none;padding:8px 13px;border-radius:6px;
font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.7px;transition:.15s}
nav a:hover{color:#000;background:var(--lime)}
main{max-width:1040px;margin:0 auto;padding:26px 18px 64px}
.hero{position:relative;overflow:hidden;border-radius:16px;margin-bottom:26px;
padding:48px 36px;border:1px solid var(--line);
background:linear-gradient(120deg,#0e1620,#16242f 60%,#0e1620)}
.hero:before{content:"";position:absolute;top:-40%;right:-8%;width:52%;height:180%;
background:linear-gradient(180deg,var(--lime),transparent);opacity:.10;transform:skewX(-18deg)}
.hero:after{content:"";position:absolute;top:-40%;right:9%;width:13%;height:180%;
background:var(--mag);opacity:.13;transform:skewX(-18deg)}
.hero h1{position:relative;margin:0;font-size:48px;line-height:.94;font-weight:900;
font-style:italic;text-transform:uppercase;letter-spacing:-.5px}
.hero h1 em{color:var(--lime)}
.hero p{position:relative;margin:14px 0 0;color:var(--muted);max-width:580px;font-size:15px}
.hero .stats{position:relative;display:flex;gap:30px;margin-top:24px;flex-wrap:wrap}
.hero .stats b{display:block;font-size:28px;font-weight:900;font-style:italic;color:#fff}
.hero .stats span{font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;
padding:22px;margin-bottom:20px}
.card h2{margin:0 0 4px;font-size:23px;font-weight:900;font-style:italic;
text-transform:uppercase;letter-spacing:.3px}
h3{font-size:12px;color:var(--lime);text-transform:uppercase;letter-spacing:1.4px;
font-weight:800;margin:22px 0 10px}
table{width:100%;border-collapse:collapse;font-size:14px}
th{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;
text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
td{padding:12px 10px;border-bottom:1px solid var(--line);vertical-align:middle}
tr:last-child td{border-bottom:none}
table tr:hover{background:var(--panel2)}
.rank{font-weight:900;font-style:italic;font-size:20px;color:var(--muted);width:46px}
.lead-1{box-shadow:inset 3px 0 0 var(--gold)}.lead-1 .rank{color:var(--gold)}
.lead-2{box-shadow:inset 3px 0 0 #cdd6df}.lead-2 .rank{color:#cdd6df}
.lead-3{box-shadow:inset 3px 0 0 #e09b56}.lead-3 .rank{color:#e09b56}
.tname{font-weight:800;font-size:15px}
.pts{font-weight:900;font-style:italic;font-size:20px;color:var(--lime)}
.badge{display:inline-block;padding:3px 9px;border-radius:5px;font-size:10px;
font-weight:800;text-transform:uppercase;letter-spacing:.6px;
background:rgba(198,255,0,.14);color:var(--lime);border:1px solid rgba(198,255,0,.25)}
.badge.zone{background:rgba(26,209,255,.12);color:var(--cyan);border-color:rgba(26,209,255,.28)}
.tag{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.btn{display:inline-block;background:var(--lime);color:#06120a;border:none;
padding:11px 20px;border-radius:8px;font-size:13px;font-weight:900;cursor:pointer;
text-transform:uppercase;letter-spacing:.6px;text-decoration:none;transition:.15s}
.btn:hover{box-shadow:0 0 22px rgba(198,255,0,.45);transform:translateY(-1px)}
.btn.sec{background:transparent;color:var(--lime);border:1px solid var(--lime)}
.btn.sec:hover{background:var(--lime);color:#06120a}
.btn.danger{background:var(--mag);color:#fff}
.btn.danger:hover{box-shadow:0 0 22px rgba(255,47,122,.45)}
label{display:block;font-size:11px;font-weight:800;text-transform:uppercase;
letter-spacing:.6px;color:var(--muted);margin:14px 0 5px}
input,select{width:100%;padding:11px 12px;border:1px solid var(--line);border-radius:8px;
font-size:14px;background:var(--bg2);color:var(--txt)}
input:focus,select:focus{outline:none;border-color:var(--lime)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:0 18px}
.row{display:flex;gap:16px;flex-wrap:wrap}.row>*{flex:1;min-width:200px}
fieldset{border:1px solid var(--line);border-radius:10px;margin:14px 0;padding:6px 16px 16px}
legend{font-weight:900;font-style:italic;text-transform:uppercase;font-size:13px;
color:var(--lime);padding:0 8px}
.opt{display:inline-block;margin:6px 16px 6px 0;font-weight:600;font-size:14px;color:var(--txt)}
.opt input{width:auto;margin-right:6px}
.muted{color:var(--muted);font-size:13px}
.vs{font-weight:900;font-style:italic;color:var(--muted);padding:0 8px}
.win{color:var(--lime);font-weight:900}
.pending{color:var(--gold)}
.flash{background:rgba(198,255,0,.10);border:1px solid var(--lime);color:var(--lime);
padding:13px 17px;border-radius:10px;margin-bottom:20px;font-weight:700}
.hint{background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:16px;
font-size:13px;color:var(--muted)}
a{color:var(--lime)}

/* ===================== LANDING PAGE ===================== */
.lp{max-width:1000px;margin:0 auto;padding:0 18px}
.lp-hero{position:relative;overflow:hidden;border-radius:20px;margin:22px 0;
padding:60px 40px;border:1px solid var(--line);
background:linear-gradient(125deg,#0b141d,#16242f 55%,#0b141d)}
.lp-hero:before{content:"";position:absolute;top:-50%;right:-12%;width:60%;height:200%;
background:linear-gradient(180deg,var(--lime),transparent);opacity:.12;transform:skewX(-18deg)}
.lp-hero:after{content:"";position:absolute;top:-50%;right:10%;width:14%;height:200%;
background:var(--mag);opacity:.14;transform:skewX(-18deg)}
.lp-eyebrow{position:relative;display:inline-block;font-size:12px;font-weight:800;
letter-spacing:2px;text-transform:uppercase;color:#06120a;background:var(--lime);
padding:5px 12px;border-radius:6px;margin-bottom:18px}
.lp-hero h1{position:relative;margin:0;font-size:54px;line-height:.95;font-weight:900;
font-style:italic;text-transform:uppercase;letter-spacing:-1px;max-width:760px}
.lp-hero h1 em{color:var(--lime)}
.lp-sub{position:relative;margin:18px 0 0;font-size:19px;color:#cdd8e0;max-width:600px;line-height:1.45}
.lp-cta-row{position:relative;display:flex;gap:14px;align-items:center;margin-top:28px;flex-wrap:wrap}
.btn-xl{font-size:16px;padding:16px 30px;border-radius:10px}
.lp-trust{position:relative;margin-top:18px;font-size:13px;color:var(--muted);
display:flex;gap:18px;flex-wrap:wrap}
.lp-trust b{color:var(--lime)}
.lp-counter{position:relative;display:inline-flex;align-items:center;gap:9px;margin-top:22px;
background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:30px;
padding:8px 16px;font-size:14px;font-weight:700}
.lp-counter .dot{width:9px;height:9px;border-radius:50%;background:var(--lime);
box-shadow:0 0 10px var(--lime);animation:pulse 1.6s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.lp-section{padding:46px 0;border-top:1px solid var(--line)}
.lp-section>h2{text-align:center;font-size:30px;font-weight:900;font-style:italic;
text-transform:uppercase;margin:0 0 8px}
.lp-section .lead{text-align:center;color:var(--muted);max-width:620px;margin:0 auto 34px;font-size:16px}
.lp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px}
.benefit{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:24px}
.benefit .ic{font-size:30px;line-height:1}
.benefit h3{color:var(--txt);text-transform:none;letter-spacing:0;font-size:17px;
font-weight:800;margin:14px 0 6px}
.benefit p{margin:0;color:var(--muted);font-size:14px}
.steps{counter-reset:s;display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px}
.step{position:relative;background:var(--panel);border:1px solid var(--line);
border-radius:14px;padding:26px 22px 22px}
.step:before{counter-increment:s;content:counter(s);position:absolute;top:-16px;left:22px;
width:38px;height:38px;border-radius:10px;background:var(--lime);color:#06120a;
font-weight:900;font-style:italic;font-size:20px;display:flex;align-items:center;justify-content:center}
.step h3{margin:10px 0 6px;text-transform:none;letter-spacing:0;color:var(--txt);font-size:16px;font-weight:800}
.step p{margin:0;color:var(--muted);font-size:14px}
.manifesto{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--lime);
border-radius:0 16px 16px 0;padding:30px 34px;max-width:760px;margin:0 auto}
.manifesto h2{font-size:24px;font-style:italic;text-transform:uppercase;font-weight:900;margin:0 0 12px}
.manifesto h2 em{color:var(--lime)}
.manifesto p{margin:0;color:#c2ccd4;font-size:16px;line-height:1.6}
.manifesto .sign{margin-top:14px;color:var(--muted);font-size:14px;font-style:italic}
.founders{background:linear-gradient(125deg,#171108,#1f1407);border:1px solid #5a4412;
border-radius:16px;padding:32px;text-align:center;margin-top:10px}
.founders h2{color:var(--gold);font-style:italic;text-transform:uppercase;margin:0 0 8px;font-size:26px}
.founders p{color:#e8d9b0;max-width:620px;margin:0 auto;font-size:15px}
.lp-form-wrap{background:var(--panel);border:1px solid var(--line);border-radius:18px;
padding:32px;max-width:560px;margin:0 auto}
.lp-form-wrap h2{font-size:26px;margin:0 0 6px;text-align:center}
.faq-item{background:var(--panel);border:1px solid var(--line);border-radius:12px;
padding:18px 20px;margin-bottom:12px}
.faq-item h3{color:var(--txt);text-transform:none;letter-spacing:0;font-size:16px;
font-weight:800;margin:0 0 6px}
.faq-item p{margin:0;color:var(--muted);font-size:14px}
.lp-final{text-align:center;padding:54px 0}
.lp-final h2{font-size:34px;font-style:italic;text-transform:uppercase;font-weight:900;margin:0 0 22px}
.lp-foot{text-align:center;color:var(--muted);font-size:13px;padding:30px 0 10px;border-top:1px solid var(--line)}
.success{background:rgba(198,255,0,.08);border:1px solid var(--lime);border-radius:18px;
padding:40px;text-align:center;max-width:560px;margin:0 auto}
.success .big{font-size:54px}
.success h2{font-size:26px;margin:10px 0}
.ref-banner{position:relative;background:rgba(198,255,0,.12);border:1px solid var(--lime);
border-radius:12px;padding:12px 18px;margin-bottom:22px;font-weight:700;color:var(--lime)}
.reflink{display:flex;gap:8px;align-items:center;background:var(--bg2);border:1px solid var(--line);
border-radius:10px;padding:12px 14px;margin:14px 0;font-family:var(--font-mono,monospace);
font-size:14px;word-break:break-all;color:var(--txt)}
.share-row{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:6px}
.share-row a{text-decoration:none}
.share-wa{background:#25D366;color:#06210f}
.share-wa:hover{box-shadow:0 0 22px rgba(37,211,102,.45)}
.countdown{position:relative;display:flex;gap:10px;margin-top:26px;flex-wrap:wrap}
.cd-cell{background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:12px;
padding:12px 16px;min-width:76px;text-align:center}
.cd-cell b{display:block;font-size:34px;font-weight:900;font-style:italic;color:var(--lime);
line-height:1;font-variant-numeric:tabular-nums}
.cd-cell span{font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted)}
.cd-label{position:relative;margin:12px 0 0;font-size:13px;color:var(--muted)}
.cd-label strong{color:var(--lime)}

.consent{display:flex;gap:10px;align-items:flex-start;margin-top:18px;text-transform:none;
letter-spacing:0;font-weight:500;font-size:12.5px;color:var(--muted);line-height:1.45}
.consent input{width:auto;flex:0 0 auto;margin-top:2px}
.consent a{color:var(--lime)}
.legal{max-width:760px;margin:0 auto;color:#c2ccd4;font-size:15px;line-height:1.65}
.legal h3{color:var(--lime);margin-top:26px}
.legal a{color:var(--lime)}
.brand .mark{width:30px;height:auto;flex:0 0 auto}

@media(max-width:600px){
.lp-hero{padding:40px 22px}.lp-hero h1{font-size:36px}.lp-sub{font-size:16px}
.lp-section>h2{font-size:24px}.lp-final h2{font-size:26px}.lp-final{padding:38px 0}
.lp-section{padding:36px 0}
.hero{padding:32px 22px}.hero h1{font-size:32px}
main{padding:20px 14px 48px}
.card{padding:18px}.card h2{font-size:20px}
.lp-form-wrap{padding:22px 18px}
.grid2{grid-template-columns:1fr}
.lp-hero h1,.hero h1{letter-spacing:-.5px}
nav a{padding:7px 10px;font-size:11px}
table{font-size:13px}th,td{padding:9px 7px}
.hero .stats{gap:18px}.hero .stats b{font-size:23px}
.btn-xl{font-size:15px;padding:14px 22px}
.cd-cell{min-width:62px;padding:10px 12px}.cd-cell b{font-size:26px}
}
"""


# Marque compacte (caducée padel) pour le header + le favicon — cohérente avec le logo.
MARK_SVG = (
    '<svg class="mark" viewBox="0 0 32 38" xmlns="http://www.w3.org/2000/svg" '
    'aria-hidden="true">'
    '<circle cx="16" cy="15" r="14" fill="#c6ff00"/>'
    '<ellipse cx="16" cy="12" rx="6.5" ry="8.5" fill="#070b10"/>'
    '<rect x="14.4" y="19" width="3.2" height="16" rx="1.6" fill="#070b10"/>'
    '<path d="M16 21 C13.4 22.5 13.4 25 16 26.5 C18.6 28 18.6 30.5 16 32 '
    'C13.6 33.4 13.6 35 16 36" fill="none" stroke="#c6ff00" stroke-width="2.2" '
    'stroke-linecap="round"/>'
    '<circle cx="16" cy="20" r="2.1" fill="#c6ff00"/>'
    '</svg>')


def carte_svg(prenom, profession=None, zone=None):
    """Carte perso partageable (1080×1080, format story/post Instagram).
    « Membre fondateur » brandé, à screenshoter pour partager. Pas d'emoji
    (risque de rendu). Couleurs du thème LIV/Kings. (S11 viralité)."""
    nom = e((prenom or "").strip()) or "Membre fondateur"
    sous = " · ".join(x for x in (e(profession or ""), e(zone or "")) if x)
    sous_txt = (f'<text x="540" y="700" text-anchor="middle" fill="#9fb0c0" '
                f'font-size="34" font-weight="600" '
                f'font-family="Helvetica,Arial,sans-serif">{sous}</text>') if sous else ""
    # Caducée agrandi, centré, repris de MARK_SVG (échelle ×6 ≈ 192px).
    mark = (
        '<g transform="translate(444,150) scale(6)">'
        '<circle cx="16" cy="15" r="14" fill="#c6ff00"/>'
        '<ellipse cx="16" cy="12" rx="6.5" ry="8.5" fill="#070b10"/>'
        '<rect x="14.4" y="19" width="3.2" height="16" rx="1.6" fill="#070b10"/>'
        '<path d="M16 21 C13.4 22.5 13.4 25 16 26.5 C18.6 28 18.6 30.5 16 32 '
        'C13.6 33.4 13.6 35 16 36" fill="none" stroke="#c6ff00" stroke-width="2.2" '
        'stroke-linecap="round"/>'
        '<circle cx="16" cy="20" r="2.1" fill="#c6ff00"/></g>')
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" '
        'width="1080" height="1080" font-family="Helvetica,Arial,sans-serif">'
        '<rect width="1080" height="1080" fill="#070b10"/>'
        '<rect x="24" y="24" width="1032" height="1032" rx="40" fill="none" '
        'stroke="#1b2733" stroke-width="2"/>'
        + mark +
        # Bandeau « MEMBRE FONDATEUR »
        '<rect x="360" y="470" width="360" height="58" rx="29" fill="#c6ff00"/>'
        '<text x="540" y="509" text-anchor="middle" fill="#070b10" font-size="28" '
        'font-weight="900" letter-spacing="3" '
        'font-style="italic">MEMBRE FONDATEUR</text>'
        # Prénom (gros)
        f'<text x="540" y="630" text-anchor="middle" fill="#ffffff" font-size="92" '
        f'font-weight="900" font-style="italic">{nom}</text>'
        + sous_txt +
        # Pied de carte
        '<text x="540" y="900" text-anchor="middle" fill="#c6ff00" font-size="40" '
        'font-weight="900" font-style="italic">LIGUE PADEL SANTÉ</text>'
        '<text x="540" y="948" text-anchor="middle" fill="#5d6b78" font-size="28" '
        'letter-spacing="4">ÎLE-DE-FRANCE · SAISON 1 · SEPT. 2026</text>'
        '<text x="540" y="1010" text-anchor="middle" fill="#ff2f7a" font-size="30" '
        'font-weight="700">padel-med-league.fr</text>'
        '</svg>')


def page_carte(ref_from):
    """Page de la carte perso à partager (S11). Affiche la carte SVG + lien de
    partage + instructions story. Repli gracieux si le code est inconnu."""
    prenom = ref_from["prenom"] if ref_from else None
    profession = ref_from["profession"] if ref_from else None
    zone = ref_from["zone"] if ref_from else None
    code = ref_from["ref_code"] if ref_from else None
    svg = carte_svg(prenom, profession, zone)
    lien = f"{BASE_URL}/?ref={e(code)}" if code else BASE_URL
    corps = f"""
    <div class="card" style="max-width:560px;margin:0 auto;text-align:center">
      <h1 style="margin:.2em 0">Ta carte de fondateur·rice</h1>
      <p class="muted">Fais une capture d'écran et partage-la en story Instagram ou
      sur WhatsApp pour inviter tes collègues. Ton lien de parrainage est dessous.</p>
      <div style="max-width:340px;margin:18px auto;border-radius:18px;overflow:hidden;
           border:1px solid var(--line)">{svg}</div>
      <div class="reflink"><span>{e(lien)}</span></div>
      <div class="share-row" style="margin-top:14px">
        <a class="btn share-wa" href="https://wa.me/?text={urllib.parse.quote(
            'Je rejoins la Ligue Padel Santé — rejoins-moi : ' + lien)}">📲 WhatsApp</a>
        <button type="button" class="btn sec"
          onclick="navigator.clipboard.writeText('{lien}');this.textContent='✓ Copié !'">📋 Copier le lien</button>
        <a class="btn sec" href="/?ref={e(code)}">← Retour</a>
      </div>
      <p class="muted" style="margin-top:14px;font-size:13px">Astuce : ouvre cette page
      sur ton téléphone, capture la carte, puis poste-la en story.</p>
    </div>"""
    return page("Ma carte", corps, nav=False)


def page(titre, corps, flash=None, nav=True, og_title=None, og_desc=None):
    # nav=False sur les pages publiques (landing, confidentialité) : on ne montre pas
    # les liens vers la démo tant qu'on est en pré-lancement.
    # og_title/og_desc : aperçu de lien personnalisé (ex. parrainage). L'image OG
    # reste l'image statique (les crawlers ne lisent pas le SVG dynamique).
    og_t = og_title or "Ligue Padel Santé — Île-de-France"
    og_d = og_desc or ("Le championnat de padel des soignants d'Île-de-France. "
                       "Un adversaire à ton niveau, près de chez toi. Inscription gratuite.")
    nav = """
    <a href="/">Accueil</a>
    <a href="/classements">Classements</a>
    <a href="/calendrier">Calendrier</a>
    <a href="/tournant">Tournant</a>
    <a href="/joueurs">Joueurs</a>
    <a href="/inscription">S'inscrire</a>
    <a href="/admin">Admin</a>""" if nav else ""
    fl = f'<div class="flash">{e(flash)}</div>' if flash else ""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titre)} — Ligue Padel Santé</title>
<meta property="og:title" content="{e(og_t)}">
<meta property="og:description" content="{e(og_d)}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:url" content="{BASE_URL}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">

<style>{CSS}</style></head>
<body><header>
<div class="brand">{MARK_SVG}
<span>Ligue Padel Santé<small>ÎLE-DE-FRANCE</small></span></div>
<nav>{nav}</nav></header>
<main>{fl}{corps}</main></body></html>"""


def badge_niveau(niv):
    n = int(round(niv))
    lib = NIVEAUX.get(n, ("", ""))[0]
    return f'<span class="badge">Niv {niv} · {e(lib)}</span>'


def nom_equipe(conn, eid):
    if eid is None:
        return "—"
    r = conn.execute("SELECT nom FROM equipes WHERE id=?", (eid,)).fetchone()
    return r["nom"] if r else "?"


# ---- Pages -----------------------------------------------------------------

# Compte à rebours jusqu'au coup d'envoi de la Saison 1 (1er sept 2026, heure de Paris).
# Hors f-string pour éviter le conflit des accolades JS avec le formatage Python.
_COUNTDOWN_JS = '''
<script>
(function(){
  var target = new Date("2026-09-01T00:00:00+02:00").getTime();
  function pad(n){ return (n<10?"0":"")+n; }
  function set(id,v){ var el=document.getElementById(id); if(el) el.textContent=v; }
  var timer = setInterval(tick, 1000);
  function tick(){
    var diff = target - Date.now();
    if(diff <= 0){
      clearInterval(timer);
      var cd = document.getElementById("cd");
      if(cd) cd.innerHTML = "<div class='cd-cell' style='min-width:auto;padding:14px 24px'><b>C'est parti !</b></div>";
      return;
    }
    set("cd-d", Math.floor(diff/86400000));
    set("cd-h", pad(Math.floor(diff/3600000)%24));
    set("cd-m", pad(Math.floor(diff/60000)%60));
    set("cd-s", pad(Math.floor(diff/1000)%60));
  }
  tick();
})();
</script>'''


def page_landing(sent_code=None, ref_from=None, error=None, source=None):
    n = count_waitlist()
    # Suivi d'acquisition : ?from=<source> (ex. "sihp") transmis au formulaire
    source_field = (f'<input type="hidden" name="source" value="{e(source)}">'
                    if source else "")
    # Tant qu'on a peu d'inscrits, on n'affiche PAS le nombre (un compteur bas est
    # contre-productif). Au-delà du seuil, on montrera le compteur — et plus tard le
    # détail par corps de métier (voir S9 dans STRATEGIE.md).
    SEUIL_COMPTEUR = 50
    err_banner = ""
    if error:
        err_banner = ('<div class="ref-banner" style="background:rgba(255,47,122,.12);'
                      'border-color:var(--mag);color:var(--mag)">⚠️ Pour t\'inscrire, '
                      'merci de cocher la case d\'accord sur l\'utilisation de ton '
                      'email (et de renseigner un email valide).</div>')
    if n >= SEUIL_COMPTEUR:
        compteur = (f'<span class="lp-counter"><span class="dot"></span>'
                    f'{n} soignant·e·s déjà sur la liste</span>')
    else:
        compteur = ('<span class="lp-counter"><span class="dot"></span>'
                    'Inscription ouverte — sois parmi les premiers</span>')

    # Bandeau d'invitation si on arrive via un lien de parrainage
    ref_banner = ""
    referred_field = ""
    if ref_from:
        qui = e(ref_from["prenom"]) if ref_from["prenom"] else "Un·e collègue"
        ref_banner = (f'<div class="ref-banner">👋 {qui} t\'invite à rejoindre la '
                      f'Ligue Padel Santé — vous pourrez jouer ensemble !</div>')
        referred_field = (f'<input type="hidden" name="referred_by" '
                          f'value="{e(ref_from["ref_code"])}">')

    if sent_code:
        lien = f"{BASE_URL}/?ref={e(sent_code)}"
        nb_f = compte_filleuls(sent_code)
        msg = urllib.parse.quote(
            f"Je rejoins la Ligue Padel Santé d'Île-de-France 🎾🩺 "
            f"(le championnat de padel des soignants). Rejoins-moi sur la liste "
            f"d'attente : {lien}")
        wa = f"https://wa.me/?text={msg}"
        mail = (f"mailto:?subject={urllib.parse.quote('Rejoins-moi sur la Ligue Padel Santé')}"
                f"&body={msg}")
        linkedin = f"https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(lien)}"
        # « Invite ton binôme » : le padel est un 2v2, c'est le partage n°1 (S11).
        msg_binome = urllib.parse.quote(
            "Sois mon binôme dans la Ligue Padel Santé 🎾🩺 — le championnat de "
            "padel des soignants d'Île-de-France. On s'inscrit ensemble : " + lien)
        wa_binome = f"https://wa.me/?text={msg_binome}"
        binome_cta = (
            '<div style="background:linear-gradient(135deg,rgba(198,255,0,.10),'
            'rgba(255,47,122,.08));border:1px solid var(--lime);border-radius:14px;'
            'padding:18px;margin:18px 0;text-align:center">'
            '<p style="margin:0 0 4px;font-size:18px"><strong>🤝 Invite ton binôme</strong></p>'
            '<p class="muted" style="margin:0 0 12px;font-size:14px">Le padel se joue à '
            'deux. Embarque ton/ta partenaire de jeu maintenant — vous serez appariés '
            'ensemble dès l\'ouverture.</p>'
            f'<a class="btn share-wa btn-xl" href="{wa_binome}">📲 Inviter mon binôme</a></div>')
        # Rang de parrain + podium anonymisé (gamification RGPD-safe : aucun nom tiers).
        rang, total_p = rang_parrain(sent_code)
        podium = ""
        if total_p >= 3:
            tops = [n for (_rc, _pr, n) in classement_parrains()[:3]]
            medals = ["🥇", "🥈", "🥉"]
            cells = "".join(
                f'<div style="flex:1"><div style="font-size:24px">{medals[i]}</div>'
                f'<div style="font-weight:900;color:var(--lime);font-size:20px">{tops[i]}</div>'
                f'<div class="muted" style="font-size:12px">invitations</div></div>'
                for i in range(len(tops)))
            moi = (f'<p style="margin:10px 0 0;font-size:14px">Tu es <strong>'
                   f'{rang}<sup>e</sup></strong> sur <strong>{total_p}</strong> '
                   f'parrains actifs 🔥</p>') if rang else (
                   '<p style="margin:10px 0 0;font-size:14px" class="muted">Lance-toi : '
                   'une seule invitation et tu entres au classement des parrains.</p>')
            podium = (
                '<div style="text-align:center;background:var(--bg2);border:1px solid '
                'var(--line);border-radius:12px;padding:16px 18px;margin:14px 0">'
                '<strong>🏆 Le podium des parrains</strong>'
                f'<div style="display:flex;gap:8px;margin-top:12px">{cells}</div>{moi}</div>')
        # Paliers de récompense du parrainage
        items, prochain = "", None
        for seuil, titre, detail in REF_MILESTONES:
            atteint = nb_f >= seuil
            if not atteint and prochain is None:
                prochain = (seuil, titre)
            coche = "✅" if atteint else f'<span class="tag">{seuil}&nbsp;inv.</span>'
            items += (f'<div style="display:flex;gap:10px;align-items:flex-start;margin:7px 0;'
                      f'{"" if atteint else "opacity:.55"}"><span>{coche}</span>'
                      f'<span><strong>{titre}</strong> '
                      f'<span class="muted">— {detail}</span></span></div>')
        if prochain:
            reste = prochain[0] - nb_f
            entete = (f'<strong>Tu as parrainé {nb_f} personne·s.</strong> Plus que '
                      f'<strong>{reste}</strong> pour débloquer « {e(prochain[1])} » 🔓')
        else:
            entete = f'<strong>🏆 Tu as tout débloqué ({nb_f} parrainages) — merci !</strong>'
        incentive = (f'<div style="text-align:left;background:var(--bg2);border:1px solid '
                     f'var(--line);border-radius:12px;padding:16px 18px;margin:14px 0">'
                     f'<p style="margin:0 0 10px">{entete}</p>{items}</div>')
        # Résultats du sondage (révélés après le vote)
        counts = waitlist_pref_counts()
        total_votes = sum(counts.values())
        bars = ""
        for label, vals in PREF_BUCKETS:
            n = sum(counts.get(v, 0) for v in vals)
            pct = round(100 * n / total_votes) if total_votes else 0
            bars += (f'<div style="margin:9px 0"><div style="display:flex;'
                     f'justify-content:space-between;font-size:13px;margin-bottom:4px">'
                     f'<span>{label}</span><span class="muted">{pct}% · {n}</span></div>'
                     f'<div style="background:var(--bg2);border:1px solid var(--line);'
                     f'border-radius:6px;height:12px;overflow:hidden">'
                     f'<div style="width:{pct}%;height:100%;background:var(--lime)"></div>'
                     f'</div></div>')
        sondage = (f'<div style="text-align:left;background:var(--bg2);border:1px solid '
                   f'var(--line);border-radius:12px;padding:16px 18px;margin:18px 0">'
                   f'<strong>🗳️ Ce que préfèrent les {total_votes} inscrit·e·s :</strong>'
                   f'{bars}</div>') if total_votes else ""
        # CTA n°1 : le canal WhatsApp est le moyen FIABLE d'être prévenu (les emails
        # peuvent finir en spam/promotions). Abonnés anonymes = aucun numéro exposé.
        whatsapp_cta = (
            '<div style="background:rgba(37,211,102,.12);border:1px solid #25D366;'
            'border-radius:14px;padding:18px;margin:4px 0 18px;text-align:center">'
            '<p style="margin:0 0 4px;font-size:19px"><strong>💬 Suis le canal officiel '
            'WhatsApp</strong></p>'
            '<p class="muted" style="margin:0 0 12px;font-size:14px">'
            '⚠️ <strong>Nos emails peuvent tomber dans tes spams ou l\'onglet '
            'Promotions.</strong> Sur le canal WhatsApp, tu es sûr·e d\'être prévenu·e à '
            'l\'ouverture (date, créneaux, clubs). Diffusion seulement — '
            '<strong>ton numéro reste privé</strong>, personne ne le voit.</p>'
            f'<a class="btn share-wa btn-xl" href="{e(WHATSAPP_URL)}">💬 Suivre le canal '
            'WhatsApp</a></div>') if WHATSAPP_URL else (
            '<div style="background:rgba(255,206,58,.10);border:1px solid var(--gold);'
            'border-radius:12px;padding:14px 16px;margin:4px 0 16px;text-align:center">'
            '<p class="muted" style="margin:0;font-size:14px">📌 <strong>Ajoute '
            'contact@padel-med-league.fr à tes contacts</strong> pour ne pas rater nos '
            'emails (ils peuvent tomber en spam/promotions).</p></div>')
        form_section = f"""<div class="success" id="rejoindre">
        <div class="big">🎾</div>
        <h2>Tu es sur la liste. Bienvenue !</h2>
        <p class="muted">On te préviendra dès l'ouverture — tu seras
        prioritaire pour le <strong>Club des Fondateurs</strong>.</p>
        {whatsapp_cta}
        {binome_cta}
        {sondage}
        <p style="margin-top:6px"><strong>Fais grandir la ligue — et débloque des
        avantages 👇</strong><br><span class="muted">Plus tu invites de collègues,
        plus tu montes dans la file et plus tu débloques de paliers.</span></p>
        {incentive}
        {podium}
        <div class="reflink"><span>{e(lien)}</span></div>
        <div class="share-row">
          <a class="btn share-wa" href="{wa}">📲 WhatsApp</a>
          <a class="btn sec" href="{linkedin}">💼 LinkedIn</a>
          <a class="btn sec" href="{mail}">✉️ Email</a>
          <button type="button" class="btn sec"
            onclick="navigator.clipboard.writeText('{lien}');this.textContent='✓ Copié !'">📋 Copier le lien</button>
        </div>
        <p style="margin-top:12px"><a class="btn sec" href="/carte?ref={e(sent_code)}">🎴
        Voir ma carte de fondateur·rice à partager</a></p>
        <p class="muted" style="margin-top:10px;font-size:13px">📸 <strong>Instagram :</strong>
        ouvre ta carte, capture-la et partage-la en story avec ton lien.</p></div>"""
    else:
        # Bouton « S'inscrire avec Google » (si configuré)
        google_block = ""
        if GOOGLE_CLIENT_ID:
            login_uri = f"{BASE_URL}/auth/google"
            if ref_from:
                login_uri += f"?ref={e(ref_from['ref_code'])}"
            google_block = f"""
            <div id="g_id_onload" data-client_id="{e(GOOGLE_CLIENT_ID)}"
                 data-login_uri="{login_uri}" data-ux_mode="redirect"></div>
            <div class="g_id_signin" data-type="standard" data-text="signup_with"
                 data-shape="pill" data-logo_alignment="center"
                 style="display:flex;justify-content:center"></div>
            <script src="https://accounts.google.com/gsi/client" async></script>
            <div style="text-align:center;color:var(--muted);margin:16px 0;font-size:13px">
            — ou avec ton email —</div>"""
        form_section = f"""<div class="lp-form-wrap" id="rejoindre">
        <h2>Rejoins la liste d'attente</h2>
        <p class="muted" style="text-align:center;margin:0 0 18px">
        Gratuit · 30 secondes · zéro engagement. On te prévient au lancement.</p>
        {err_banner}
        {google_block}
        <form method="post" action="/rejoindre">{referred_field}{source_field}
          <label>Email *</label>
          <input name="email" type="email" required placeholder="toi@exemple.fr">
          <div class="grid2">
            <div><label>Prénom (optionnel)</label><input name="prenom" placeholder="Camille"></div>
            <div><label>Profession</label><select name="profession">{opts(PROFESSIONS)}</select></div>
          </div>
          <div class="grid2">
            <div><label>Ta zone</label><select name="zone">{opts(ZONES)}</select></div>
            <div><label>Comment préfères-tu jouer ?</label>
              <select name="a_partenaire">{opts(PREF_OPTIONS)}</select></div>
          </div>
          <label class="consent">
            <input type="checkbox" name="consent" value="1" required>
            <span>J'accepte que mon email soit utilisé pour me prévenir du lancement
            de la Ligue Padel Santé et organiser la ligue. Je peux me désinscrire à tout
            moment. Voir la <a href="/confidentialite" target="_blank">politique de
            confidentialité</a>.</span>
          </label>
          <button class="btn btn-xl" type="submit"
            style="width:100%;margin-top:18px">Je réserve ma place →</button>
        </form>
        <p class="muted" style="text-align:center;margin:14px 0 0;font-size:12px">
        On ne partage et ne revend jamais ton email. Désinscription en 1 clic.</p></div>"""

    corps = f"""<div class="lp">
    {ref_banner}
    <div class="lp-hero">
      <span class="lp-eyebrow">Pré-lancement · Saison 1</span>
      <h1>Le championnat de padel des <em>soignants</em> d'Île-de-France</h1>
      <p class="lp-sub"><strong>Débutant qui se lance</strong> ou <strong>joueur
      confirmé</strong> : on t'apparie avec des partenaires et adversaires
      <strong>exactement à ton niveau</strong>, près de chez toi, toutes les 2 semaines.
      Tu trouves le créneau, tu joues — on gère tout le reste.</p>
      <div class="lp-cta-row">
        <a class="btn btn-xl" href="#rejoindre">Rejoindre la liste d'attente →</a>
      </div>
      <div class="lp-trust">
        <span>✅ <b>À ton niveau</b>, garanti</span>
        <span>✅ <b>100% gratuit</b></span>
        <span>✅ Tous les <b>soignants</b></span>
        <span>✅ <b>9 zones</b> en IDF</span>
      </div>
      <div class="countdown" id="cd" role="timer" aria-label="Compte à rebours avant le lancement">
        <div class="cd-cell"><b id="cd-d">--</b><span>Jours</span></div>
        <div class="cd-cell"><b id="cd-h">--</b><span>Heures</span></div>
        <div class="cd-cell"><b id="cd-m">--</b><span>Min</span></div>
        <div class="cd-cell"><b id="cd-s">--</b><span>Sec</span></div>
      </div>
      <p class="cd-label">Coup d'envoi de la <strong>Saison 1</strong> — 1ᵉʳ septembre 2026.
      Prends ta place avant.</p>
      {compteur}
    </div>

    <div class="lp-section">
      <h2>Débutant ou confirmé : toujours à <em>ton</em> niveau</h2>
      <p class="lead">La hantise au padel, c'est de tomber sur des joueurs trop forts —
      ou trop faibles. Ici, l'appariement par niveau (et une cote qui s'affine à chaque
      match) te garantit des parties <strong>serrées et plaisantes</strong>, quel que
      soit ton point de départ.</p>
      <div class="lp-grid">
        <div class="benefit" style="border-color:rgba(198,255,0,.35)">
          <div class="ic">🌱</div><h3>Tu débutes ?</h3>
          <p>C'est <strong>le moment de t'y mettre</strong>. Tu joues face à des gens
          comme toi, dans une ambiance bienveillante — <strong>zéro match humiliant</strong>.
          Pas de partenaire ? On t'en trouve un à ton niveau.</p></div>
        <div class="benefit" style="border-color:rgba(255,47,122,.35)">
          <div class="ic">🔥</div><h3>Tu joues déjà bien ?</h3>
          <p><strong>Fini les matchs déséquilibrés et ennuyeux.</strong> Tu trouves
          enfin des partenaires et adversaires <strong>à ta hauteur</strong> — et des
          soignants avec qui tu as de vraies <strong>affinités</strong>, sur le terrain
          comme en dehors.</p></div>
      </div>
    </div>

    <div class="lp-section">
      <div class="manifesto">
        <h2>100% gratuit. <em>0% business.</em></h2>
        <p>On n'est pas une boîte. La Ligue Padel Santé, c'est juste une bande de
        soignants qui aiment le padel et qui voulaient jouer plus souvent, contre
        des gens sympas. <strong>Pas de pub, on ne revend pas tes données, on ne
        gagne pas un centime là-dessus.</strong> On l'a monté pour le plaisir de
        jouer et de rencontrer du monde. C'est tout. 🎾</p>
        <p class="sign">— Des soignants, pour des soignants.</p>
      </div>
    </div>

    <div class="lp-section">
      <h2>Le padel, sans la prise de tête</h2>
      <p class="lead">Organiser des matchs réguliers, trouver des adversaires de son
      niveau, gérer un classement… c'est pénible. La ligue fait tout ça pour toi.</p>
      <div class="lp-grid">
        <div class="benefit"><div class="ic">🎯</div><h3>Adversaire à ta mesure</h3>
          <p>Un algorithme t'apparie par niveau et par zone géographique. Des matchs
          serrés, jamais ridicules ni perdus d'avance.</p></div>
        <div class="benefit"><div class="ic">🤙</div><h3>Zéro logistique</h3>
          <p>Pas de planning rigide. Tu reçois ton adversaire et ses coordonnées,
          vous calez le créneau qui vous arrange.</p></div>
        <div class="benefit"><div class="ic">📈</div><h3>Une vraie progression</h3>
          <p>Classement en direct et cote qui évolue à chaque match. De quoi
          se prendre au jeu sur toute la saison.</p></div>
        <div class="benefit"><div class="ic">🩺</div><h3>Entre soignants</h3>
          <p>Médecins, kinés, infirmiers, dentistes, étudiants… On décompresse,
          on réseaute, on se chambre. Bonne ambiance garantie.</p></div>
      </div>
    </div>

    <div class="lp-section">
      <h2>Comment ça marche</h2>
      <p class="lead">Quatre étapes, et tu joues. Aucun binôme fixe imposé.</p>
      <div class="steps">
        <div class="step"><h3>Inscris-toi</h3><p>Rejoins la liste d'attente
          maintenant. On t'écrit dès l'ouverture.</p></div>
        <div class="step"><h3>Choisis ton mode</h3><p>En <strong>solo</strong>
          (partenaires tournants) ou en <strong>équipe</strong> avec ton binôme. Tu
          peux changer <strong>à chaque journée</strong>.</p></div>
        <div class="step"><h3>Reçois ton match</h3><p>Toutes les 2 semaines, des
          partenaires et adversaires à ton niveau, dans ta zone. Tu cales le créneau
          dans le club de ton choix.</p></div>
        <div class="step"><h3>Joue, score &amp; grimpe</h3><p>Tu entres le score, le
          classement et ta cote s'actualisent seuls. Officiel joué ? Tu peux
          enchaîner des <strong>matchs amicaux</strong> quand tu veux.</p></div>
      </div>
    </div>

    <div class="lp-section">
      <div class="founders">
        <h2>🏆 Club des Fondateurs</h2>
        <p>Les <strong>50 premières équipes</strong> inscrites rejoignent le Club des
        Fondateurs : badge exclusif sur leur profil, mise en avant sur notre Instagram,
        et avantages chez nos clubs partenaires. La liste d'attente te donne la
        priorité. <strong>Ne traîne pas.</strong></p>
      </div>
    </div>

    <div class="lp-section">{form_section}</div>

    <div class="lp-section">
      <h2>Questions fréquentes</h2>
      <div style="max-width:680px;margin:0 auto">
        <div class="faq-item"><h3>C'est vraiment gratuit ? Où est l'arnaque ?</h3>
          <p>Pas d'arnaque : c'est <strong>100% gratuit et ça le restera</strong>. On
          ne gagne rien là-dessus — pas de pub, pas de revente de données. C'est un
          projet de soignants, monté pour le plaisir de jouer et de se rencontrer.
          Seul le terrain (réservé par les joueurs) est à votre charge, comme
          d'habitude.</p></div>
        <div class="faq-item"><h3>Je suis débutant, c'est pour moi ?</h3><p>Absolument.
          L'appariement par niveau fait que tu joues contre des gens comme toi. On
          part de 3/7 (« je tiens l'échange »).</p></div>
        <div class="faq-item"><h3>Je ne suis pas médecin.</h3><p>Aucun souci : la ligue
          est ouverte à <strong>tous les professionnels de santé</strong> — kinés,
          infirmiers, dentistes, pharmaciens, sages-femmes, étudiants en santé…</p></div>
        <div class="faq-item"><h3>Je n'ai pas de partenaire.</h3><p>Aucun problème :
          tu peux jouer <strong>en solo</strong> — à chaque journée, on t'attribue
          un·e partenaire (et des adversaires) à ton niveau. Tu as un binôme ?
          Inscrivez-vous en <strong>équipe</strong>. Et tu peux <strong>changer de
          formule à chaque journée</strong> : c'est une seule et même ligue, avec
          un classement individuel <em>et</em> un classement par équipe.</p></div>
        <div class="faq-item"><h3>Ça prend combien de temps ?</h3><p>Un match toutes les
          2 semaines, au créneau que vous choisissez. Tenable même avec des gardes.</p></div>
        <div class="faq-item"><h3>Qui réserve le terrain ?</h3><p>Les joueurs, dans le
          club de leur choix (4Padel, Casa Padel, Padel Horizon…). On vous met en
          relation et on suggère les clubs proches.</p></div>
      </div>
    </div>

    <div class="lp-final">
      <h2>Prêt à entrer dans la ligue ?</h2>
      <a class="btn btn-xl" href="#rejoindre">Rejoindre la liste d'attente →</a>
      <div class="lp-foot">Ligue Padel Santé · Île-de-France — un projet par et pour
      les soignants. 🎾🩺<br>📸 Instagram :
      <a href="https://instagram.com/padelmedleague">@padelmedleague</a>
      {('· 💬 <a href="' + e(WHATSAPP_URL) + '">Canal WhatsApp</a>') if WHATSAPP_URL else ''}
      · <a href="/confidentialite">Confidentialité</a></div>
    </div>
    </div>""" + _COUNTDOWN_JS
    # OG personnalisé quand on arrive via un lien de parrainage (aperçu partagé).
    og_title = og_desc = None
    if ref_from:
        qui = (ref_from["prenom"] or "").strip() or "Un·e collègue"
        og_title = f"{qui} t'invite dans la Ligue Padel Santé"
        og_desc = ("Le championnat de padel des soignants d'Île-de-France. "
                   "Inscris-toi gratuitement et jouez ensemble.")
    return page("Accueil", corps, nav=False, og_title=og_title, og_desc=og_desc)


def page_confidentialite():
    corps = """<div class="card legal">
    <h2 style="font-size:28px">Politique de confidentialité</h2>
    <p class="muted">Dernière mise à jour : juin 2026</p>
    <p>La Ligue Padel Santé Île-de-France attache de l'importance à la protection de tes
    données. Cette page explique, en clair, quelles informations nous recueillons via la
    liste d'attente, pourquoi, et quels sont tes droits.</p>

    <h3>Qui est responsable ?</h3>
    <p>La Ligue Padel Santé, projet à but non lucratif porté par des professionnels de
    santé. Pour toute question ou demande relative à tes données :
    <a href="mailto:contact@padel-med-league.fr">contact@padel-med-league.fr</a>.</p>

    <h3>Quelles données collectons-nous ?</h3>
    <ul>
      <li><strong>Ton email</strong> (obligatoire) — pour te recontacter.</li>
      <li><strong>Facultatif</strong> : prénom, profession, zone géographique et
      préférence de jeu — pour préparer la ligue et son appariement.</li>
      <li>Un <strong>code de parrainage</strong> et, le cas échéant, le code de la
      personne qui t'a invité — pour le programme de parrainage.</li>
    </ul>
    <p>Nous ne collectons <strong>aucune donnée de santé</strong> te concernant.</p>

    <h3>Pourquoi ? (finalités)</h3>
    <ul>
      <li>Te prévenir de l'ouverture de la ligue et t'informer du projet.</li>
      <li>Organiser la ligue et l'appariement par niveau et par zone.</li>
      <li>Gérer le programme de parrainage.</li>
    </ul>
    <p>La base légale de ce traitement est <strong>ton consentement</strong>, recueilli
    via la case que tu coches au moment de l'inscription.</p>

    <h3>Qui y a accès ?</h3>
    <p>Uniquement l'équipe de la ligue. <strong>Nous ne vendons, ne louons et ne
    partageons jamais ton email</strong> à des tiers à des fins commerciales. Tes données
    sont stockées et traitées pour notre compte par nos prestataires techniques
    (hébergement du site et de la base de données, et — à l'avenir — l'outil d'envoi des
    emails), qui agissent comme sous-traitants et ne les utilisent pas pour leur compte.</p>

    <h3>Combien de temps les conservons-nous ?</h3>
    <p>Jusqu'au lancement de la ligue puis pendant la durée de ta participation, ou
    jusqu'à ce que tu demandes ta désinscription / la suppression de tes données.</p>

    <h3>Tes droits</h3>
    <p>Tu disposes à tout moment d'un droit d'accès, de rectification, d'effacement,
    d'opposition, de limitation, de portabilité, et du droit de <strong>retirer ton
    consentement</strong>. Pour les exercer, écris-nous à
    <a href="mailto:contact@padel-med-league.fr">contact@padel-med-league.fr</a> : il te
    suffit d'un mot, la désinscription se fait en quelques secondes. Tu peux aussi
    introduire une réclamation auprès de la CNIL (<a href="https://www.cnil.fr"
    target="_blank">cnil.fr</a>).</p>

    <h3>Cookies</h3>
    <p>Ce site n'utilise <strong>ni cookie publicitaire, ni traceur, ni outil de mesure
    d'audience tiers</strong>. Seuls d'éventuels cookies strictement nécessaires au
    fonctionnement du site peuvent être déposés.</p>

    <p style="margin-top:28px"><a class="btn sec" href="/">← Retour à l'accueil</a></p>
    </div>"""
    return page("Confidentialité", corps, nav=False)


def page_classement(flash=None):
    table = classement()
    conn = db()
    nb_j = conn.execute("SELECT COUNT(*) c FROM journees").fetchone()["c"]
    nb_m = conn.execute("SELECT COUNT(*) c FROM matchs WHERE statut='valide'").fetchone()["c"]
    conn.close()
    lignes = ""
    for i, s in enumerate(table, 1):
        eq = s["equipe"]
        diff_sets = s["sg"] - s["sp"]
        cls = f"lead-{i}" if i <= 3 else ""
        lignes += f"""<tr class="{cls}">
        <td class="rank">{i}</td>
        <td><a href="/equipe?id={eq['id']}" style="text-decoration:none;color:inherit">
            <span class="tname">{e(eq['nom'])}</span></a><br>
            <span class="badge zone">{e(eq['zone'])}</span>
            {badge_niveau(eq['niveau'])}
            <span class="tag">cote {int(eq['rating'])}</span></td>
        <td>{s['j']}</td><td>{s['v']}</td>
        <td>{diff_sets:+d}</td>
        <td class="pts">{s['pts']}</td></tr>"""
    hero = f"""<div class="hero">
    <h1>La ligue de padel<br>des <em>soignants</em> d'Île-de-France</h1>
    <p>Un adversaire à votre niveau toutes les deux semaines, attribué
    automatiquement. Vous trouvez le terrain, vous jouez, vous entrez le score —
    le classement fait le reste.</p>
    <div class="stats">
      <div><b>{len(table)}</b><span>Équipes</span></div>
      <div><b>{nb_j}</b><span>Journées</span></div>
      <div><b>{nb_m}</b><span>Matchs joués</span></div>
      <div><b>9</b><span>Zones IDF</span></div>
    </div></div>"""
    corps = hero + f"""<div class="card"><h2>Classement général</h2>
    <p class="muted">Système suisse · cadence tous les 15 jours · barème 3/2/1/0.
    Cliquez sur une équipe pour voir son détail.</p>
    <table><tr><th>#</th><th>Équipe</th><th>J</th><th>V</th>
    <th>Δ sets</th><th>Pts</th></tr>{lignes}</table></div>"""
    return page("Classement", corps, flash)


CLASSEMENTS_VUES = [
    ("equipe", "Équipes", "Classement des équipes"),
    ("individuel", "Individuel", "La Cote d'Or — classement individuel"),
    ("profession", "Profession", "Le Trophée des Blouses — par profession"),
    ("specialite", "Spécialité", "Le Stéthoscope d'Or — par spécialité"),
    ("structure", "Établissement", "Le Derby des Établissements"),
    ("zone", "Zone", "La Carte aux Trophées — par zone"),
]


def page_classements(par="equipe", flash=None):
    titre = next((t for k, _, t in CLASSEMENTS_VUES if k == par), "Classements")
    subnav = " ".join(
        f'<a class="btn {"" if k==par else "sec"}" href="/classements?par={k}" '
        f'style="font-size:12px;padding:8px 13px">{e(lib)}</a>'
        for k, lib, _ in CLASSEMENTS_VUES)

    if par == "equipe":
        rows = ""
        for i, s in enumerate(classement(), 1):
            eq = s["equipe"]; cls = f"lead-{i}" if i <= 3 else ""
            rows += (f'<tr class="{cls}"><td class="rank">{i}</td>'
                     f'<td><a href="/equipe?id={eq["id"]}" style="text-decoration:none;color:inherit">'
                     f'<span class="tname">{e(eq["nom"])}</span></a> '
                     f'<span class="badge zone">{e(eq["zone"])}</span> '
                     f'<span class="tag">cote {int(eq["rating"])}</span></td>'
                     f'<td>{s["j"]}</td><td>{s["v"]}</td>'
                     f'<td>{s["sg"]-s["sp"]:+d}</td><td class="pts">{s["pts"]}</td></tr>')
        head = "<th>#</th><th>Équipe</th><th>J</th><th>V</th><th>Δ sets</th><th>Pts</th>"
        intro = "Système suisse · barème 3/2/1/0 · cliquez une équipe pour le détail."

    elif par == "individuel":
        _c = db()
        noms_eq = {r["id"]: r["nom"] for r in _c.execute("SELECT id, nom FROM equipes")}
        _c.close()
        rows = ""
        for i, s in enumerate(classement_joueurs(), 1):
            j = s["joueur"]; cls = f"lead-{i}" if i <= 3 else ""
            eqn = noms_eq.get(j["equipe_id"], "—")
            rows += (f'<tr class="{cls}"><td class="rank">{i}</td>'
                     f'<td><span class="tname">{e(j["nom"])}</span> '
                     f'<span class="tag">@{e(j["username"])} · {e(j["profession"] or "")} · {e(eqn)}</span></td>'
                     f'<td class="pts">{int(j["rating"])}</td>'
                     f'<td>{s["j"]}</td><td>{s["v"]}</td><td class="pts">{s["pts"]}</td></tr>')
        head = "<th>#</th><th>Joueur</th><th>Cote</th><th>J</th><th>V</th><th>Pts</th>"
        intro = "Chaque joueur porte les résultats de ses matchs. Cote = Elo individuel."

    else:  # profession / specialite / structure / zone
        rows = ""
        for i, g in enumerate(classement_par(par), 1):
            cls = f"lead-{i}" if i <= 3 else ""
            rows += (f'<tr class="{cls}"><td class="rank">{i}</td>'
                     f'<td><span class="tname">{e(g["nom"])}</span> '
                     f'<span class="tag">{g["joueurs"]} joueur·s · {g["v"]} victoires</span></td>'
                     f'<td>{g["cote_moy"]}</td><td class="pts">{g["pts_par_tete"]}</td></tr>')
        if not rows:
            rows = '<tr><td colspan="4" class="muted">Pas encore de résultats dans cette catégorie.</td></tr>'
        head = "<th>#</th><th>Groupe</th><th>Cote moy</th><th>Pts / joueur</th>"
        intro = ("Classement « par tête » (points moyens par joueur) : équitable quelle "
                 "que soit la taille du groupe.")

    corps = f"""<div class="card"><h2>Classements</h2>
    <div class="row" style="gap:6px;margin-bottom:8px">{subnav}</div></div>
    <div class="card"><h2 style="font-size:19px">{e(titre)}</h2>
    <p class="muted">{intro}</p>
    <table><tr>{head}</tr>{rows}</table></div>"""
    return page("Classements", corps, flash)


def page_calendrier(flash=None):
    conn = db()
    journees = conn.execute("SELECT * FROM journees ORDER BY numero DESC").fetchall()
    corps = ""
    if not journees:
        corps = """<div class="card"><h2>Calendrier</h2>
        <p>Aucune journée générée. Allez dans <a href="/admin">Admin</a> pour
        générer la première journée.</p></div>"""
    for j in journees:
        matchs = conn.execute(
            "SELECT * FROM matchs WHERE journee_id=? ORDER BY id", (j["id"],)).fetchall()
        lignes = ""
        for m in matchs:
            na = nom_equipe(conn, m["equipe_a"])
            if m["statut"] == "repos":
                lignes += f"""<tr><td>{e(na)}</td><td class="vs">repos</td>
                <td></td><td><span class="tag">journée de repos (bye)</span></td></tr>"""
                continue
            nb = nom_equipe(conn, m["equipe_b"])
            if m["statut"] == "valide":
                va = '<span class="win">' if m["vainqueur"] == m["equipe_a"] else "<span>"
                vb = '<span class="win">' if m["vainqueur"] == m["equipe_b"] else "<span>"
                res = f"{va}{e(na)}</span> <span class='vs'>{m['sets_a']}-{m['sets_b']}</span> {vb}{e(nb)}</span>"
                lignes += f"""<tr><td colspan="3">{res}</td>
                <td class="tag">{e(m['detail'])}</td></tr>"""
            else:
                lignes += f"""<tr><td>{e(na)}</td><td class="vs">vs</td>
                <td>{e(nb)}</td><td><a class="btn sec" href="/score?match={m['id']}">
                Saisir le score</a></td></tr>"""
        corps += f"""<div class="card"><h2>Journée {j['numero']}</h2>
        <table>{lignes}</table></div>"""
    conn.close()
    return page("Calendrier", corps, flash)


def joueur_nom(conn, pid):
    if pid is None:
        return "—"
    r = conn.execute("SELECT nom, username FROM joueurs WHERE id=?", (pid,)).fetchone()
    return f"{r['nom']}" if r else "?"


def page_tournant(flash=None):
    conn = db()
    nb_solo = conn.execute("SELECT COUNT(*) c FROM joueurs WHERE mode='solo'").fetchone()["c"]
    journees = conn.execute("SELECT * FROM journees_solo ORDER BY numero DESC").fetchall()
    intro = f"""<div class="card"><h2>Mode tournant (Americano)</h2>
    <p class="muted">Pas de binôme fixe : à chaque journée, le système te donne un
    <strong>partenaire</strong> et des <strong>adversaires différents</strong>,
    regroupés par niveau (4 joueurs par terrain). Ton score est individuel — tu
    grimpes à <a href="/classements?par=individuel">La Cote d'Or</a>.
    <br><strong>{nb_solo}</strong> joueur·s inscrits en solo.
    <a href="/inscription">S'inscrire en solo →</a></p></div>"""
    corps = intro
    if not journees:
        corps += """<div class="card"><p>Aucune journée tournante générée. Allez
        dans <a href="/admin">Admin</a> pour en générer une.</p></div>"""
    for j in journees:
        ms = conn.execute("SELECT * FROM matchs_solo WHERE journee_id=? ORDER BY id",
                          (j["id"],)).fetchall()
        lignes = ""
        for m in ms:
            if m["statut"] == "repos":
                lignes += (f'<tr><td colspan="2">{e(joueur_nom(conn, m["a1"]))}</td>'
                           f'<td class="tag">journée de repos</td></tr>')
                continue
            a = f'{e(joueur_nom(conn, m["a1"]))} & {e(joueur_nom(conn, m["a2"]))}'
            b = f'{e(joueur_nom(conn, m["b1"]))} & {e(joueur_nom(conn, m["b2"]))}'
            if m["statut"] == "valide":
                wa = '<span class="win">' if m["vainqueur_side"] == "A" else "<span>"
                wb = '<span class="win">' if m["vainqueur_side"] == "B" else "<span>"
                lignes += (f'<tr><td colspan="2">{wa}{a}</span> '
                           f'<span class="vs">{m["sets_a"]}-{m["sets_b"]}</span> '
                           f'{wb}{b}</span></td><td class="tag">{e(m["detail"])}</td></tr>')
            else:
                lignes += (f'<tr><td>{a} <span class="vs">vs</span> {b}</td><td></td>'
                           f'<td><a class="btn sec" href="/score-solo?match={m["id"]}">'
                           f'Saisir le score</a></td></tr>')
        corps += (f'<div class="card"><h2>Journée tournante {j["numero"]}</h2>'
                  f'<table>{lignes}</table></div>')
    conn.close()
    return page("Tournant", corps, flash)


def page_score_solo(match_id, flash=None):
    conn = db()
    m = conn.execute("SELECT * FROM matchs_solo WHERE id=?", (match_id,)).fetchone()
    if not m or m["statut"] != "a_jouer":
        conn.close()
        return page("Score", "<div class='card'>Match introuvable ou déjà saisi.</div>")
    a = f'{e(joueur_nom(conn, m["a1"]))} & {e(joueur_nom(conn, m["a2"]))}'
    b = f'{e(joueur_nom(conn, m["b1"]))} & {e(joueur_nom(conn, m["b2"]))}'
    conn.close()
    corps = f"""<div class="card"><h2>Saisir le score (tournant)</h2>
    <p><strong>{a}</strong> <span class="vs">vs</span> <strong>{b}</strong></p>
    <form method="post" action="/score-solo">
    <input type="hidden" name="match" value="{match_id}">
    <table><tr><th></th><th>Équipe A</th><th>Équipe B</th></tr>
    <tr><td>Set 1</td><td><input name="s1a" type="number" min="0" max="9" required></td>
        <td><input name="s1b" type="number" min="0" max="9" required></td></tr>
    <tr><td>Set 2</td><td><input name="s2a" type="number" min="0" max="9" required></td>
        <td><input name="s2b" type="number" min="0" max="9" required></td></tr>
    <tr><td>Set 3</td><td><input name="s3a" type="number" min="0" max="9"></td>
        <td><input name="s3b" type="number" min="0" max="9"></td></tr></table>
    <br><button class="btn" type="submit">Valider le score</button></form></div>"""
    return page("Saisir le score", corps, flash)


def page_equipe(eid):
    conn = db()
    eq = conn.execute("SELECT * FROM equipes WHERE id=?", (eid,)).fetchone()
    if not eq:
        conn.close()
        return page("Équipe", "<div class='card'>Équipe introuvable.</div>")
    joueurs = conn.execute("SELECT * FROM joueurs WHERE equipe_id=?", (eid,)).fetchall()
    jl = ""
    for j in joueurs:
        jl += f"""<tr><td><strong>{e(j['nom'])}</strong>
        <br><span class="tag">@{e(j['username'])}</span></td>
        <td><strong>{e(j['profession'] or '')}</strong>
        <br><span class="tag">{e(j['statut'] or '')}</span></td>
        <td>{e('' if j['specialite'] in (None,'—') else j['specialite'])}</td>
        <td>{e(j['structure'])}</td>
        <td>{badge_niveau(j['niveau'])}</td></tr>"""
    matchs = conn.execute(
        "SELECT * FROM matchs WHERE (equipe_a=? OR equipe_b=?) AND statut='valide' "
        "ORDER BY id DESC", (eid, eid)).fetchall()
    hist = ""
    for m in matchs:
        adv = m["equipe_b"] if m["equipe_a"] == eid else m["equipe_a"]
        mine_a = m["equipe_a"] == eid
        sp = m["sets_a"] if mine_a else m["sets_b"]
        sc = m["sets_b"] if mine_a else m["sets_a"]
        issue = '<span class="win">Victoire</span>' if sp > sc else '<span class="pending">Défaite</span>'
        hist += f"""<tr><td>{e(nom_equipe(conn,adv))}</td>
        <td>{sp}-{sc}</td><td>{issue}</td></tr>"""
    conn.close()
    if not hist:
        hist = "<tr><td colspan='3' class='muted'>Aucun match joué pour l'instant.</td></tr>"
    corps = f"""<div class="card"><h2>{e(eq['nom'])}</h2>
    <p><span class="badge zone">{e(eq['zone'])}</span>
    {badge_niveau(eq['niveau'])}
    <span class="tag">cote actuelle {int(eq['rating'])}</span></p>
    <h3>Joueurs</h3>
    <table><tr><th>Nom</th><th>Profession</th><th>Spécialité</th><th>Structure</th>
    <th>Niveau</th></tr>{jl}</table></div>
    <div class="card"><h3>Historique des matchs</h3>
    <table><tr><th>Adversaire</th><th>Score</th><th>Issue</th></tr>{hist}</table></div>"""
    return page(eq["nom"], corps)


def opts(liste, sel=None):
    return "".join(
        f'<option value="{e(v)}"{" selected" if v==sel else ""}>{e(v)}</option>'
        for v in liste)


def niveau_options():
    return "".join(
        f'<option value="{k}">{k} · {e(v[0])} — {e(v[1])}</option>'
        for k, v in NIVEAUX.items())


def page_inscription(flash=None):
    datalist = "".join(f'<option value="{e(s)}">' for s in EXEMPLES_STRUCTURES)
    corps = f"""<div class="card"><h2>S'inscrire (individuel)</h2>
    <p class="muted">Ouvert à <strong>tous les professionnels de santé</strong>.
    Pas sûr de votre niveau ? <a href="/niveau">Estimez-le avec le questionnaire</a>.</p>
    <form method="post" action="/inscription">
    <fieldset><legend>Comment veux-tu jouer ?</legend>
      <label class="opt"><input type="radio" name="mode" value="classique" checked>
        <strong>Avec mon binôme</strong> — équipe fixe toute la saison
        (tu trouves ton partenaire dans l'annuaire)</label>
      <label class="opt"><input type="radio" name="mode" value="solo">
        <strong>En solo (tournant)</strong> — pas de partenaire fixe : à chaque
        journée, le système te donne un partenaire ET des adversaires différents.
        Classement individuel.</label>
    </fieldset>
    <div class="grid2">
      <div><label>Nom</label><input name="nom" required placeholder="Prénom Nom (Dr, M., Mme…)"></div>
      <div><label>Pseudo (pour être retrouvé par votre partenaire)</label>
        <input name="username" placeholder="ex. a.lefort"></div>
    </div>
    <div class="grid2">
      <div><label>Email</label><input name="email" type="email" placeholder="vous@exemple.fr"></div>
      <div><label>Téléphone</label><input name="tel"></div>
    </div>
    <div class="row">
      <div><label>Profession</label><select name="profession">{opts(PROFESSIONS)}</select></div>
      <div><label>Statut d'exercice</label><select name="statut">{opts(STATUTS)}</select></div>
      <div><label>Spécialité (optionnel)</label><select name="spe">{opts(SPECIALITES)}</select></div>
    </div>
    <label>Structure / lieu d'exercice</label>
    <input name="structure" list="dl_struct" placeholder="ex. Hôpital Pitié-Salpêtrière, Cabinet libéral Paris 15…">
    <datalist id="dl_struct">{datalist}</datalist>
    <div class="row">
      <div><label>Code postal</label>
        <input name="cp" placeholder="ex. 75014" maxlength="5">
        <span class="muted">détecte la zone automatiquement</span></div>
      <div><label>Zone</label><select name="zone">
        <option value="auto" selected>↳ Détecter via le code postal</option>
        {opts(ZONES)}</select></div>
      <div><label>Niveau (auto-évaluation 3-7)</label>
        <select name="niv">{niveau_options()}</select></div>
    </div>
    <br><button class="btn" type="submit">M'inscrire</button></form></div>
    <div class="card hint"><strong>Repères de niveau (échelle 3-7)</strong><br>
    """ + "<br>".join(
        f"<b>{k}</b> · {e(v[0])} — {e(v[1])}" for k, v in NIVEAUX.items()) + """
    <br><br><span class="muted">Autres portes d'entrée prévues : classement FFT,
    catégorie de tournoi habituelle (P25→P1000).</span></div>"""
    return page("S'inscrire", corps, flash)


def page_joueurs(q=None, flash=None):
    conn = db()
    params, where = [], ""
    if q:
        where = ("WHERE lower(j.nom) LIKE ? OR lower(j.username) LIKE ? "
                 "OR lower(j.email) LIKE ? OR lower(j.specialite) LIKE ? "
                 "OR lower(j.profession) LIKE ?")
        like = f"%{q.lower()}%"
        params = [like] * 5
    rows = conn.execute(
        f"SELECT j.*, e.nom AS equipe_nom FROM joueurs j "
        f"LEFT JOIN equipes e ON e.id=j.equipe_id {where} ORDER BY j.equipe_id IS NOT NULL, j.nom",
        params).fetchall()
    conn.close()
    libres = [r for r in rows if r["equipe_id"] is None]
    pris = [r for r in rows if r["equipe_id"] is not None]

    def ligne(r):
        eq = (f'<a href="/equipe?id={r["equipe_id"]}">{e(r["equipe_nom"])}</a>'
              if r["equipe_id"] else '<span class="badge">Cherche partenaire</span>')
        spe = r['specialite'] if r['specialite'] and r['specialite'] != '—' else ''
        sous = " · ".join(x for x in (r['statut'], spe) if x)
        return f"""<tr><td><strong>{e(r['nom'])}</strong>
        <br><span class="tag">@{e(r['username'])}</span></td>
        <td><strong>{e(r['profession'] or '')}</strong>
        <br><span class="tag">{e(sous)}</span>
        <br><span class="tag">{e(r['structure'] or '')}</span></td>
        <td><span class="badge zone">{e(r['zone'] or '?')}</span></td>
        <td>{badge_niveau(r['niveau']) if r['niveau'] else ''}</td>
        <td>{eq}</td></tr>"""

    tbl_libres = ("".join(ligne(r) for r in libres)
                  or '<tr><td colspan="5" class="muted">Personne ne cherche de partenaire pour le moment.</td></tr>')
    tbl_pris = ("".join(ligne(r) for r in pris)
                or '<tr><td colspan="5" class="muted">Aucune équipe formée.</td></tr>')
    head = "<tr><th>Joueur</th><th>Profession / structure</th><th>Zone</th><th>Niveau</th><th>Équipe</th></tr>"
    corps = f"""<div class="card"><h2>Annuaire des joueurs</h2>
    <form method="get" action="/joueurs" class="row" style="align-items:flex-end">
      <div><label>Rechercher (nom, pseudo, email, spécialité)</label>
      <input name="q" value="{e(q or '')}" placeholder="ex. cardio, a.lefort…"></div>
      <div style="flex:0 0 auto"><button class="btn" type="submit">Rechercher</button></div>
    </form></div>
    <div class="card"><h3>🟢 En recherche de partenaire ({len(libres)})</h3>
    <p class="muted">Trouvez quelqu'un, puis <a href="/equipe-former">formez votre équipe</a>.</p>
    <table>{head}{tbl_libres}</table></div>
    <div class="card"><h3>Joueurs déjà en équipe ({len(pris)})</h3>
    <table>{head}{tbl_pris}</table></div>"""
    return page("Joueurs", corps, flash)


def page_former_equipe(flash=None):
    corps = f"""<div class="card"><h2>Former une équipe</h2>
    <p class="muted">Associez deux joueurs déjà inscrits. Chacun se retrouve par
    son <strong>pseudo</strong> ou son <strong>email</strong> (voir l'
    <a href="/joueurs">annuaire</a>). Le niveau et la cote de l'équipe sont
    calculés automatiquement.</p>
    <form method="post" action="/equipe-former">
    <label>Nom de l'équipe</label><input name="equipe" required placeholder="ex. Les Coronaires">
    <div class="grid2">
      <div><label>Vous (pseudo ou email)</label>
        <input name="moi" required placeholder="a.lefort"></div>
      <div><label>Votre partenaire (pseudo ou email)</label>
        <input name="partenaire" required placeholder="s.mercier"></div>
    </div>
    <div class="row">
      <div><label>Zone de l'équipe</label><select name="zone">
        <option value="auto" selected>↳ Reprendre votre zone</option>{opts(ZONES)}</select></div>
      <div><label>Zone secondaire (optionnel)</label>
        <select name="zone2"><option value="">—</option>{opts(ZONES)}</select></div>
    </div>
    <br><button class="btn" type="submit">Créer l'équipe</button></form>
    <p class="muted" style="margin-top:14px">Dans la version finale : votre
    partenaire recevra une <strong>invitation à accepter</strong> avant que
    l'équipe soit validée.</p></div>"""
    return page("Former une équipe", corps, flash)


def page_niveau(flash=None, resultat=None):
    qs = ""
    for key, libelle, opts in QUESTIONS:
        o = "".join(
            f'<label class="opt"><input type="radio" name="{key}" value="{val}"'
            f'{" checked" if val==0 else ""}>{e(txt)}</label>'
            for txt, val in opts)
        qs += f'<fieldset><legend>{e(libelle)}</legend>{o}</fieldset>'
    res = ""
    if resultat is not None:
        lib, desc = NIVEAUX[resultat]
        res = f"""<div class="flash"><strong>Niveau estimé : {resultat} · {e(lib)}</strong>
        <br>{e(desc)}<br>Reportez ce niveau dans le formulaire d'
        <a href="/inscription">inscription</a>.</div>"""
    corps = f"""<div class="card"><h2>Estimer mon niveau (questionnaire)</h2>
    <p class="muted">Pour qui ne sait pas se situer (porte D). Répondez, le niveau
    3-7 est estimé automatiquement.</p>{res}
    <form method="post" action="/niveau">{qs}
    <br><button class="btn" type="submit">Estimer mon niveau</button></form></div>"""
    return page("Estimer mon niveau", corps, flash)


def page_score(match_id, flash=None):
    conn = db()
    m = conn.execute("SELECT * FROM matchs WHERE id=?", (match_id,)).fetchone()
    if not m or m["statut"] != "a_jouer":
        conn.close()
        return page("Score", "<div class='card'>Match introuvable ou déjà saisi.</div>")
    na = nom_equipe(conn, m["equipe_a"]); nb = nom_equipe(conn, m["equipe_b"])
    conn.close()
    corps = f"""<div class="card"><h2>Saisir le score</h2>
    <p><strong>{e(na)}</strong> <span class="vs">vs</span> <strong>{e(nb)}</strong></p>
    <p class="muted">Format 2 sets gagnants. Laissez le set 3 vide si le match
    s'est terminé 2-0.</p>
    <form method="post" action="/score">
    <input type="hidden" name="match" value="{match_id}">
    <table><tr><th></th><th>{e(na)}</th><th>{e(nb)}</th></tr>
    <tr><td>Set 1</td><td><input name="s1a" type="number" min="0" max="9" required></td>
        <td><input name="s1b" type="number" min="0" max="9" required></td></tr>
    <tr><td>Set 2</td><td><input name="s2a" type="number" min="0" max="9" required></td>
        <td><input name="s2b" type="number" min="0" max="9" required></td></tr>
    <tr><td>Set 3</td><td><input name="s3a" type="number" min="0" max="9"></td>
        <td><input name="s3b" type="number" min="0" max="9"></td></tr></table>
    <br><button class="btn" type="submit">Valider le score</button></form>
    <p class="muted" style="margin-top:14px">Dans la version finale : l'adversaire
    confirmera ou contestera (délai 5 j) avant validation définitive.</p></div>"""
    return page("Saisir le score", corps, flash)


def page_admin(flash=None):
    conn = db()
    nb_eq = conn.execute("SELECT COUNT(*) c FROM equipes").fetchone()["c"]
    nb_j = conn.execute("SELECT COUNT(*) c FROM journees").fetchone()["c"]
    nb_att = conn.execute(
        "SELECT COUNT(*) c FROM matchs WHERE statut='a_jouer'").fetchone()["c"]
    conn.close()
    wl = waitlist_all()
    nb_parraines = waitlist_nb_parraines()
    wl_rows = "".join(
        f"<tr><td>{e(w['email'])}</td><td>{e(w['prenom'] or '')}</td>"
        f"<td>{e(w['profession'] or '')}</td><td>{e(w['zone'] or '')}</td>"
        f"<td>{e(w['a_partenaire'] or '')}</td>"
        f"<td>{e(w.get('source') or '—')}</td>"
        f"<td><span class='tag'>{e(w['ref_code'] or '')}</span></td>"
        f"<td>{e(w['referred_by'] or '—')}</td>"
        f"<td class='tag'>{e(w['created'] or '')}</td></tr>"
        for w in wl) or '<tr><td colspan="9" class="muted">Aucune inscription pour l\'instant.</td></tr>'
    corps = f"""<div class="card"><h2>Administration</h2>
    <p class="muted">{nb_eq} équipes · {nb_j} journées générées · {nb_att} matchs
    en attente de score.</p>
    <h3>📋 Liste d'attente ({len(wl)}) · dont {nb_parraines} par parrainage</h3>
    <p class="muted">Inscrits via la landing page. Exportez les emails pour vos
    relances de lancement. « Code » = lien de parrainage personnel ; « Parrain » =
    code de celui qui l'a invité.</p>
    <table><tr><th>Email</th><th>Prénom</th><th>Profession</th><th>Zone</th>
    <th>Préférence</th><th>Source</th><th>Code</th><th>Parrain</th><th>Date</th></tr>{wl_rows}</table>
    <form method="post" action="/admin/wl-delete" class="row" style="align-items:flex-end;margin-top:14px"
      onsubmit="return confirm('Supprimer cette entrée de la liste d\\'attente ?')">
      <div><label>Supprimer une entrée (email)</label>
        <input name="email" type="email" placeholder="email à retirer"></div>
      <div style="flex:0 0 auto"><button class="btn danger" type="submit">Supprimer</button></div>
    </form></div>
    <div class="card">
    <h3 style="margin-top:0">Outils de simulation</h3>
    <h3>Générer la prochaine journée</h3>
    <p class="muted">Lance l'appariement suisse : chaque équipe reçoit un adversaire
    de niveau proche (cote Elo), géographiquement proche, qu'elle n'a pas déjà
    rencontré. 100 % automatique.</p>
    <form method="post" action="/admin/generer" style="display:inline">
    <button class="btn" type="submit">⚙️ Générer la journée (équipes)</button></form>
    <form method="post" action="/admin/generer-solo" style="display:inline;margin-left:8px">
    <button class="btn sec" type="submit">🔄 Générer la journée tournante (solo)</button></form>
    <h3 style="margin-top:24px">Réinitialiser la démo</h3>
    <p class="muted">Recharge les équipes de démonstration et rejoue la journée 1.</p>
    <form method="post" action="/admin/reset" onsubmit="return confirm('Réinitialiser toute la base ?')">
    <button class="btn danger" type="submit">↺ Réinitialiser</button></form></div>"""
    return page("Admin", corps, flash)


# ===========================================================================
# SERVEUR HTTP
# ===========================================================================

class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, body, code=200):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def _form(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        return urllib.parse.parse_qs(raw, keep_blank_values=True)

    def _cookie(self, name):
        for part in (self.headers.get("Cookie", "") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return None

    def _apercu_ok(self):
        """Vrai si le visiteur a déverrouillé la démo/admin (cookie d'aperçu valide)."""
        return bool(APERCU_CODE) and self._cookie("apercu") == APERCU_CODE

    def log_message(self, *args):
        pass  # silence

    # Pages accessibles sans déverrouillage (pré-lancement : seule la préinscription).
    PUBLIC_GET = {"/", "/confidentialite", "/apercu", "/favicon.svg",
                  "/favicon.ico", "/carte", "/carte.svg"}
    PUBLIC_POST = {"/rejoindre", "/auth/google", "/apercu"}

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        flash = q.get("flash", [None])[0]
        # Verrou pré-lancement : tout ce qui n'est pas public exige le déverrouillage.
        if u.path not in self.PUBLIC_GET and not self._apercu_ok():
            self._redirect("/")
            return
        try:
            if u.path == "/":
                ok = q.get("ok", [None])[0]
                ref = q.get("ref", [None])[0]
                err = q.get("err", [None])[0]
                src = q.get("from", [None])[0]
                self._send(page_landing(sent_code=ok,
                                        ref_from=waitlist_par_code(ref),
                                        error=err, source=src))
            elif u.path == "/apercu":
                # Déverrouillage de la démo/admin via ?cle=<APERCU_CODE>
                cle = q.get("cle", [""])[0]
                if APERCU_CODE and cle == APERCU_CODE:
                    self.send_response(303)
                    self.send_header("Location", "/classement")
                    self.send_header(
                        "Set-Cookie",
                        f"apercu={APERCU_CODE}; Path=/; HttpOnly; "
                        "Max-Age=2592000; SameSite=Lax")
                    self.end_headers()
                else:
                    self._redirect("/")
            elif u.path in ("/favicon.svg", "/favicon.ico"):
                data = MARK_SVG.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Cache-Control", "max-age=86400")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif u.path == "/carte":
                ref = q.get("ref", [None])[0]
                self._send(page_carte(waitlist_par_code(ref)))
            elif u.path == "/carte.svg":
                ref = waitlist_par_code(q.get("ref", [None])[0])
                svg = carte_svg(
                    ref["prenom"] if ref else None,
                    ref["profession"] if ref else None,
                    ref["zone"] if ref else None).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
                self.send_header("Cache-Control", "max-age=300")
                self.send_header("Content-Length", str(len(svg)))
                self.end_headers()
                self.wfile.write(svg)
            elif u.path == "/confidentialite":
                self._send(page_confidentialite())
            elif u.path == "/classement":
                self._send(page_classement(flash))
            elif u.path == "/classements":
                self._send(page_classements(q.get("par", ["equipe"])[0], flash))
            elif u.path == "/calendrier":
                self._send(page_calendrier(flash))
            elif u.path == "/tournant":
                self._send(page_tournant(flash))
            elif u.path == "/score-solo":
                self._send(page_score_solo(int(q.get("match", [0])[0]), flash))
            elif u.path == "/equipe":
                self._send(page_equipe(int(q.get("id", [0])[0])))
            elif u.path == "/inscription":
                self._send(page_inscription(flash))
            elif u.path == "/joueurs":
                self._send(page_joueurs(q.get("q", [""])[0], flash))
            elif u.path == "/equipe-former":
                self._send(page_former_equipe(flash))
            elif u.path == "/niveau":
                self._send(page_niveau(flash))
            elif u.path == "/score":
                self._send(page_score(int(q.get("match", [0])[0]), flash))
            elif u.path == "/admin":
                self._send(page_admin(flash))
            else:
                self._send(page("404", "<div class='card'>Page introuvable.</div>"), 404)
        except Exception as ex:
            self._send(page("Erreur", f"<div class='card'>Erreur : {e(ex)}</div>"), 500)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        f = self._form()

        def g(k, d=""):
            return f.get(k, [d])[0].strip()

        # Verrou pré-lancement : seules les actions publiques sont permises.
        if u.path not in self.PUBLIC_POST and not self._apercu_ok():
            self._redirect("/")
            return

        if u.path == "/inscription":
            zone = g("zone")
            if zone in ("", "auto"):
                zone = zone_from_cp(g("cp")) or "Centre"  # détection par code postal
            conn = db()
            existe = g("username") and conn.execute(
                "SELECT 1 FROM joueurs WHERE lower(username)=?",
                (g("username").lower(),)).fetchone()
            if existe:
                conn.close()
                self._send(page_inscription(
                    f"Le pseudo « {g('username')} » est déjà pris, choisissez-en un autre."))
                return
            mode = "solo" if g("mode") == "solo" else "classique"
            _, un = creer_joueur(
                conn, g("nom"), username=g("username") or None, email=g("email"),
                telephone=g("tel"), profession=g("profession"), statut=g("statut"),
                specialite=g("spe"), structure=g("structure"),
                niveau=int(g("niv", 4)), zone=zone, cp=g("cp"), mode=mode)
            conn.commit(); conn.close()
            if mode == "solo":
                self._redirect("/tournant?flash=" + urllib.parse.quote(
                    f"Inscription réussie en mode tournant ! Pseudo : @{un} (zone "
                    f"{zone}). À chaque journée, tu recevras un partenaire et des "
                    f"adversaires différents."))
            else:
                self._redirect("/joueurs?flash=" + urllib.parse.quote(
                    f"Inscription réussie ! Votre pseudo : @{un} (zone {zone}). "
                    f"Trouvez un partenaire puis formez votre équipe."))

        elif u.path == "/equipe-former":
            conn = db()
            j1 = find_joueur(conn, g("moi"))
            j2 = find_joueur(conn, g("partenaire"))
            err = None
            if not j1 or not j2:
                err = "Joueur introuvable : vérifiez les pseudos/emails (voir l'annuaire)."
            elif j1["id"] == j2["id"]:
                err = "Indiquez deux joueurs différents."
            elif j1["equipe_id"] or j2["equipe_id"]:
                err = "L'un des deux joueurs est déjà dans une équipe."
            if err:
                conn.close()
                self._send(page_former_equipe(err))
                return
            zone = g("zone")
            zone = None if zone in ("", "auto") else zone
            eid = former_equipe(conn, g("equipe"), j1["id"], j2["id"],
                                zone=zone, zone2=g("zone2") or None)
            conn.commit(); conn.close()
            self._redirect(f"/equipe?id={eid}")

        elif u.path == "/niveau":
            scores = [int(g(k, 0)) for k, _, _ in QUESTIONS]
            self._send(page_niveau(resultat=estimer_niveau(scores)))

        elif u.path == "/score":
            mid = int(g("match", 0))
            sets = []
            for a, b in (("s1a", "s1b"), ("s2a", "s2b"), ("s3a", "s3b")):
                va, vb = g(a), g(b)
                if va != "" and vb != "":
                    sets.append(f"{int(va)}-{int(vb)}")
            sa, sb, _, _ = parse_sets(sets) if sets else (0, 0, 0, 0)
            if max(sa, sb) < 2:
                self._send(page_score(mid,
                    "Score incomplet : il faut un vainqueur à 2 sets gagnants."))
            else:
                enregistrer_score(mid, sets)
                self._redirect("/calendrier?flash=" + urllib.parse.quote("Score enregistré, cotes mises à jour."))

        elif u.path == "/score-solo":
            mid = int(g("match", 0))
            sets = []
            for a, b in (("s1a", "s1b"), ("s2a", "s2b"), ("s3a", "s3b")):
                va, vb = g(a), g(b)
                if va != "" and vb != "":
                    sets.append(f"{int(va)}-{int(vb)}")
            sa, sb, _, _ = parse_sets(sets) if sets else (0, 0, 0, 0)
            if max(sa, sb) < 2:
                self._send(page_score_solo(mid,
                    "Score incomplet : il faut un vainqueur à 2 sets gagnants."))
            else:
                enregistrer_score_solo(mid, sets)
                self._redirect("/tournant?flash=" + urllib.parse.quote("Score enregistré, cotes mises à jour."))

        elif u.path == "/admin/generer":
            num = generer_journee()
            msg = f"Journée {num} générée par appariement suisse." if num else "Pas assez d'équipes."
            self._redirect("/calendrier?flash=" + urllib.parse.quote(msg))

        elif u.path == "/admin/generer-solo":
            num = generer_journee_solo()
            msg = (f"Journée tournante {num} générée (Americano)." if num
                   else "Il faut au moins 4 joueurs inscrits en solo.")
            self._redirect("/tournant?flash=" + urllib.parse.quote(msg))

        elif u.path == "/rejoindre":
            email = g("email")
            consent = g("consent")  # case RGPD : doit être cochée
            if "@" not in email or not consent:
                # email invalide ou consentement manquant : on n'enregistre rien
                self._redirect("/?err=consent#rejoindre")
            else:
                nouveau, code = add_waitlist(
                    email, prenom=g("prenom") or None,
                    profession=g("profession") or None, zone=g("zone") or None,
                    a_partenaire=g("a_partenaire") or None,
                    referred_by=g("referred_by") or None, consent=True,
                    source=(g("source") or None))
                if nouveau:
                    # Email de confirmation + synchro contact Brevo (fire-and-forget)
                    import threading
                    threading.Thread(
                        target=post_inscription_emails,
                        args=(email.strip().lower(), g("prenom") or None, code),
                        daemon=True).start()
                self._redirect("/?ok=" + code + "#rejoindre")

        elif u.path == "/auth/google":
            # Connexion Google : Google POST le jeton d'identité ici (mode redirect)
            ref = urllib.parse.parse_qs(u.query).get("ref", [None])[0]
            cred = g("credential")
            csrf_ok = (self._cookie("g_csrf_token") == g("g_csrf_token")
                       if self._cookie("g_csrf_token") else True)
            email = prenom = None
            if cred and csrf_ok and GOOGLE_CLIENT_ID:
                try:
                    from google.oauth2 import id_token
                    from google.auth.transport import requests as g_requests
                    info = id_token.verify_oauth2_token(
                        cred, g_requests.Request(), GOOGLE_CLIENT_ID)
                    if info.get("email_verified"):
                        email = info.get("email")
                        prenom = info.get("given_name")
                except Exception:
                    email = None
            if email:
                _, code = add_waitlist(email, prenom=prenom, referred_by=ref)
                self._redirect("/?ok=" + code + "#rejoindre")
            else:
                self._redirect("/?flash=" + urllib.parse.quote(
                    "La connexion Google a échoué, réessaie ou utilise ton email."))

        elif u.path == "/admin/wl-delete":
            waitlist_delete(g("email"))
            self._redirect("/admin?flash=" + urllib.parse.quote(
                f"Entrée « {g('email')} » supprimée de la liste d'attente."))

        elif u.path == "/admin/reset":
            seed()
            self._redirect("/classement?flash=" + urllib.parse.quote("Démo réinitialisée."))
        else:
            self._send(page("404", "<div class='card'>Inconnu.</div>"), 404)


def main():
    if not os.path.exists(DB_PATH):
        print("Première exécution : création de la base et des données de démo…")
        seed()
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print("=" * 60)
    print("  Ligue Padel Santé Île-de-France — PROTOTYPE")
    print("=" * 60)
    print(f"  En écoute sur {HOST}:{PORT}")
    print(f"  En local, ouvrez :  http://localhost:{PORT}")
    print("  Pour arrêter : Ctrl+C dans ce terminal.")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur. À bientôt !")


if __name__ == "__main__":
    main()
