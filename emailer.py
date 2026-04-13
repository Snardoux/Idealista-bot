"""
Module d'envoi d'email — génère un beau mail HTML récapitulatif
et l'envoie via SMTP (Gmail).
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from config import EMAIL_CONFIG, SCHOOL_LOCATION
from scraper import Listing


def _build_listing_card(listing: Listing, index: int) -> str:
    """Génère le HTML d'une carte annonce pour l'email."""
    badges = []
    if listing.rooms:
        badges.append(f'<span style="background:#e8f4fd;color:#1a73e8;padding:3px 10px;border-radius:12px;font-size:13px;font-weight:600;">🛏 {listing.rooms} ch.</span>')
    if listing.size_m2:
        badges.append(f'<span style="background:#e8f5e9;color:#2e7d32;padding:3px 10px;border-radius:12px;font-size:13px;font-weight:600;">📐 {listing.size_m2}m²</span>')
    if listing.floor:
        badges.append(f'<span style="background:#fff3e0;color:#e65100;padding:3px 10px;border-radius:12px;font-size:13px;font-weight:600;">🏢 {listing.floor}</span>')
    if listing.has_elevator:
        badges.append(f'<span style="background:#f3e5f5;color:#7b1fa2;padding:3px 10px;border-radius:12px;font-size:13px;font-weight:600;">🛗 Ascenseur</span>')
    if listing.has_ac:
        badges.append(f'<span style="background:#e0f7fa;color:#00838f;padding:3px 10px;border-radius:12px;font-size:13px;font-weight:600;">❄️ Clim</span>')

    badges_html = " ".join(badges) if badges else ""

    price_per_person = listing.price // 3 if listing.price > 0 else 0

    img_html = ""
    if listing.image_url:
        img_html = f'''
        <div style="margin-bottom:12px;">
            <img src="{listing.image_url}" alt="Photo" style="width:100%;max-height:200px;object-fit:cover;border-radius:8px;" />
        </div>'''

    description_short = listing.description[:250] + "..." if len(listing.description) > 250 else listing.description

    maps_url = f"https://www.google.com/maps/dir/{SCHOOL_LOCATION['address'].replace(' ', '+')}/{listing.address.replace(' ', '+') if listing.address else listing.district.replace('-', '+') + ',+Madrid'}"

    return f'''
    <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
            <span style="background:#1a73e8;color:white;padding:2px 10px;border-radius:8px;font-size:12px;font-weight:700;">#{index}</span>
            <span style="font-size:22px;font-weight:800;color:#1a73e8;">{listing.price}€<span style="font-size:14px;color:#6b7280;font-weight:400;">/mois</span></span>
        </div>

        <h3 style="margin:8px 0 4px;font-size:16px;color:#111827;line-height:1.3;">
            <a href="{listing.url}" style="color:#111827;text-decoration:none;">{listing.title}</a>
        </h3>

        <p style="margin:0 0 10px;font-size:13px;color:#059669;font-weight:600;">
            ≈ {price_per_person}€/personne (÷3)
        </p>

        {img_html}

        <div style="margin-bottom:10px;">
            {badges_html}
        </div>

        <p style="margin:0 0 12px;font-size:13px;color:#6b7280;line-height:1.5;">
            {description_short}
        </p>

        <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <a href="{listing.url}" style="display:inline-block;background:#1a73e8;color:white;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;">
                Voir l'annonce →
            </a>
            <a href="{maps_url}" style="display:inline-block;background:#f3f4f6;color:#374151;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;">
                📍 Itinéraire école
            </a>
        </div>
    </div>'''


def build_email_html(listings: list[Listing]) -> str:
    """Construit le corps HTML complet de l'email."""
    now = datetime.now()
    date_str = now.strftime("%A %d %B %Y").capitalize()

    cards = ""
    for i, listing in enumerate(listings, 1):
        cards += _build_listing_card(listing, i)

    # Stats rapides
    prices = [l.price for l in listings if l.price > 0]
    avg_price = sum(prices) // len(prices) if prices else 0
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0

    return f'''<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <div style="max-width:600px;margin:0 auto;padding:20px;">

        <!-- HEADER -->
        <div style="background:linear-gradient(135deg,#1a73e8,#0d47a1);border-radius:16px;padding:28px 24px;margin-bottom:20px;text-align:center;">
            <h1 style="margin:0;color:white;font-size:24px;">🏠 Alerte Idealista</h1>
            <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">{date_str}</p>
            <p style="margin:12px 0 0;background:rgba(255,255,255,0.2);display:inline-block;padding:6px 16px;border-radius:20px;color:white;font-size:16px;font-weight:700;">
                {len(listings)} nouvelle{"s" if len(listings) > 1 else ""} annonce{"s" if len(listings) > 1 else ""}
            </p>
        </div>

        <!-- STATS -->
        <div style="display:flex;gap:8px;margin-bottom:20px;text-align:center;">
            <div style="flex:1;background:white;border-radius:10px;padding:12px;border:1px solid #e5e7eb;">
                <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">Min</div>
                <div style="font-size:18px;font-weight:700;color:#059669;">{min_price}€</div>
            </div>
            <div style="flex:1;background:white;border-radius:10px;padding:12px;border:1px solid #e5e7eb;">
                <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">Moyenne</div>
                <div style="font-size:18px;font-weight:700;color:#1a73e8;">{avg_price}€</div>
            </div>
            <div style="flex:1;background:white;border-radius:10px;padding:12px;border:1px solid #e5e7eb;">
                <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">Max</div>
                <div style="font-size:18px;font-weight:700;color:#dc2626;">{max_price}€</div>
            </div>
        </div>

        <!-- ANNONCES -->
        {cards}

        <!-- FOOTER -->
        <div style="text-align:center;padding:20px;color:#9ca3af;font-size:12px;">
            <p>Bot Idealista · Recherche: Madrid · 3 ch. · Meublé · Max 2400€/mois</p>
            <p>📍 Référence: Paseo de la Castellana 93</p>
        </div>
    </div>
</body>
</html>'''


def build_no_results_email() -> str:
    """Email envoyé quand il n'y a pas de nouvelles annonces."""
    now = datetime.now()
    date_str = now.strftime("%A %d %B %Y").capitalize()

    return f'''<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <div style="max-width:600px;margin:0 auto;padding:20px;text-align:center;">
        <div style="background:linear-gradient(135deg,#6b7280,#374151);border-radius:16px;padding:28px 24px;margin-bottom:20px;">
            <h1 style="margin:0;color:white;font-size:24px;">🏠 Alerte Idealista</h1>
            <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">{date_str}</p>
        </div>
        <div style="background:white;border-radius:12px;padding:40px 24px;border:1px solid #e5e7eb;">
            <p style="font-size:40px;margin:0;">😴</p>
            <h2 style="margin:12px 0 8px;color:#374151;">Rien de neuf aujourd'hui</h2>
            <p style="color:#6b7280;font-size:14px;">Pas de nouvelles annonces correspondant à vos critères.<br>Le bot continue de surveiller !</p>
        </div>
    </div>
</body>
</html>'''


def send_email(listings: list[Listing], send_if_empty: bool = False):
    """Envoie l'email de notification."""
    config = EMAIL_CONFIG

    if not config["sender_email"] or not config["recipients"]:
        print("⚠️  Email non configuré — affichage console uniquement")
        if listings:
            print(f"\n{'='*60}")
            print(f"  🆕 {len(listings)} nouvelles annonces")
            print(f"{'='*60}")
            for l in listings:
                print(f"\n  📌 {l.title}")
                print(f"     {l.summary()}")
                print(f"     🔗 {l.url}")
        return

    if not listings and not send_if_empty:
        print("📭 Aucune annonce, pas d'email envoyé")
        return

    # Construire l'email
    msg = MIMEMultipart("alternative")
    now = datetime.now()
    count = len(listings)

    if listings:
        msg["Subject"] = f"{config['subject_prefix']} · {count} annonce{'s' if count > 1 else ''} · {now.strftime('%d/%m')}"
        html = build_email_html(listings)
    else:
        msg["Subject"] = f"{config['subject_prefix']} · Rien de neuf · {now.strftime('%d/%m')}"
        html = build_no_results_email()

    msg["From"] = config["sender_email"]
    msg["To"] = ", ".join(config["recipients"])
    msg.attach(MIMEText(html, "html"))

    # Envoi
    try:
        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["sender_email"], config["sender_password"])
            server.send_message(msg)
        print(f"✅ Email envoyé à {len(config['recipients'])} destinataire(s)")
    except Exception as e:
        print(f"❌ Erreur envoi email: {e}")
        raise
