"""
Configuration du bot Idealista
Modifie ces paramètres selon tes critères de recherche.
"""

# ─── CRITÈRES DE RECHERCHE ───────────────────────────────────────────
SEARCH_CONFIG = {
    # URL de base Idealista (location meublée, 3+ chambres, Madrid, max 2400€)
    "base_url": (
        "https://www.idealista.com/alquiler-viviendas/madrid-madrid/"
        "con-de-tres-dormitorios,de-cuatro-dormitorios,de-cinco-dormitorios-o-mas/"
        "precio-hasta_2400/amueblado_amueblados/"
        "?ordenado-por=fecha-publicacion-desc"
    ),
    # Nombre max de pages à scanner (chaque page ≈ 30 annonces)
    "max_pages": 5,
    # Filtres supplémentaires appliqués APRÈS scraping
    "filters": {
        "max_price": 2400,         # €/mois
        "min_rooms": 3,            # Nombre minimum de chambres
        "furnished_only": True,    # Meublé uniquement
    },
}

# ─── LOCALISATION DE RÉFÉRENCE (ton école) ───────────────────────────
SCHOOL_LOCATION = {
    "address": "Paseo de la Castellana 93, 28046 Madrid",
    "lat": 40.4514,
    "lng": -3.6918,
    # Temps de trajet max accepté (en minutes)
    "max_walk_minutes": 20,
    "max_transit_minutes": 40,
}

# ─── QUARTIERS PROCHES (dans le rayon de ton école) ──────────────────
# Ces quartiers sont à ~20 min à pied ou ~35 min en transports
# de Paseo de la Castellana 93 (Nuevos Ministerios)
NEARBY_DISTRICTS = [
    # ≤ 20 min à pied
    "nuevos-ministerios", "azca", "cuatro-caminos", "rios-rosas",
    "almagro", "trafalgar", "chamberi", "gaztambide", "arapiles",
    "vallehermoso", "castillejos", "estrecho", "berruguete",
    # ≤ 35-40 min en transports (metro ligne 6, 8, 10, etc.)
    "tetuan", "ciudad-lineal", "prosperidad", "chamartin",
    "salamanca", "goya", "lista", "diego-de-leon",
    "arguelles", "moncloa", "centro", "sol", "malasana",
    "chueca", "justicia", "universidad", "retiro",
    "ibiza", "pacifico", "delicias", "embajadores",
    "lavapies", "la-latina", "canal", "plaza-castilla",
    "hortaleza", "arturo-soria", "ventas",
]

# ─── EMAIL ────────────────────────────────────────────────────────────
# Supporte les variables d'environnement (pour GitHub Actions)
# OU les valeurs en dur ci-dessous (pour usage local)
import os

EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": os.getenv("IDEALISTA_EMAIL", ""),          # ← TON EMAIL GMAIL
    "sender_password": os.getenv("IDEALISTA_PASSWORD", ""),    # ← TON APP PASSWORD
    "recipients": (
        os.getenv("IDEALISTA_RECIPIENTS", "").split(",")
        if os.getenv("IDEALISTA_RECIPIENTS")
        else [
            # "toi@gmail.com",
            # "coloc1@gmail.com",
            # "coloc2@gmail.com",
        ]
    ),
    "subject_prefix": "🏠 Idealista Bot",
}

# ─── STOCKAGE ─────────────────────────────────────────────────────────
DATA_DIR = "data"
SEEN_LISTINGS_FILE = f"{DATA_DIR}/seen_listings.json"
HISTORY_FILE = f"{DATA_DIR}/history.json"
