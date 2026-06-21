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
    """)
    conn.commit()
    conn.close()


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
    cur = conn.execute(
        "INSERT INTO joueurs(username, nom, email, telephone, profession, statut, "
        "specialite, structure, niveau, zone, cp, equipe_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL)",
        (un, nom, kw.get("email"), kw.get("telephone"), kw.get("profession"),
         kw.get("statut"), kw.get("specialite"), kw.get("structure"),
         kw.get("niveau"), kw.get("zone"), kw.get("cp")))
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
    for i, m in enumerate(matchs):
        if i % 2 == 0:  # on ne joue qu'un match sur deux pour montrer les 2 états
            s = random.choice([("6-3", "6-4"), ("6-2", "4-6", "7-5"),
                                ("3-6", "6-4", "6-2"), ("6-1", "6-3")])
            enregistrer_score(m["id"], s)


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
"""


def page(titre, corps, flash=None):
    nav = """
    <a href="/">Classement</a>
    <a href="/calendrier">Calendrier</a>
    <a href="/joueurs">Joueurs</a>
    <a href="/inscription">S'inscrire</a>
    <a href="/equipe-former">Former une équipe</a>
    <a href="/admin">Admin</a>"""
    fl = f'<div class="flash">{e(flash)}</div>' if flash else ""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titre)} — Ligue Padel Santé</title><style>{CSS}</style></head>
<body><header>
<div class="brand"><span class="ball">🎾</span>
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
    Chaque joueur s'inscrit seul. Une fois inscrit, trouvez votre
    partenaire dans l'<a href="/joueurs">annuaire</a> et
    <a href="/equipe-former">formez votre équipe</a>. Pas sûr de votre niveau ?
    <a href="/niveau">Estimez-le avec le questionnaire</a>.</p>
    <form method="post" action="/inscription">
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
    corps = f"""<div class="card"><h2>Administration</h2>
    <p class="muted">{nb_eq} équipes · {nb_j} journées générées · {nb_att} matchs
    en attente de score.</p>
    <h3>Générer la prochaine journée</h3>
    <p class="muted">Lance l'appariement suisse : chaque équipe reçoit un adversaire
    de niveau proche (cote Elo), géographiquement proche, qu'elle n'a pas déjà
    rencontré. 100 % automatique.</p>
    <form method="post" action="/admin/generer">
    <button class="btn" type="submit">⚙️ Générer la journée</button></form>
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

    def log_message(self, *args):
        pass  # silence

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        flash = q.get("flash", [None])[0]
        try:
            if u.path == "/":
                self._send(page_classement(flash))
            elif u.path == "/calendrier":
                self._send(page_calendrier(flash))
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
            _, un = creer_joueur(
                conn, g("nom"), username=g("username") or None, email=g("email"),
                telephone=g("tel"), profession=g("profession"), statut=g("statut"),
                specialite=g("spe"), structure=g("structure"),
                niveau=int(g("niv", 4)), zone=zone, cp=g("cp"))
            conn.commit(); conn.close()
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

        elif u.path == "/admin/generer":
            num = generer_journee()
            msg = f"Journée {num} générée par appariement suisse." if num else "Pas assez d'équipes."
            self._redirect("/calendrier?flash=" + urllib.parse.quote(msg))

        elif u.path == "/admin/reset":
            seed()
            self._redirect("/?flash=" + urllib.parse.quote("Démo réinitialisée."))
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
