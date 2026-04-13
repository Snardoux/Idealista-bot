#!/usr/bin/env python3
"""
🏠 Idealista Bot — Point d'entrée principal
Lance le scraping + envoi email.

Usage:
    python main.py              # Scrape + email si nouvelles annonces
    python main.py --force      # Scrape + email même si rien de neuf
    python main.py --dry-run    # Scrape sans envoyer d'email
    python main.py --reset      # Remet à zéro les annonces vues
"""

import argparse
import os
import sys
import json
from datetime import datetime, timezone

from config import DATA_DIR, SEEN_LISTINGS_FILE


def main():
    parser = argparse.ArgumentParser(description="🏠 Idealista Bot — Scraper + Email")
    parser.add_argument("--force", action="store_true", help="Envoyer l'email même sans nouvelles annonces")
    parser.add_argument("--dry-run", action="store_true", help="Scraper sans envoyer d'email")
    parser.add_argument("--reset", action="store_true", help="Remettre à zéro les annonces déjà vues")
    args = parser.parse_args()

    # Reset
    if args.reset:
        if os.path.exists(SEEN_LISTINGS_FILE):
            os.remove(SEEN_LISTINGS_FILE)
            print("🔄 Fichier d'annonces vues supprimé")
        else:
            print("ℹ️  Rien à reset")
        return

    print(f"""
╔══════════════════════════════════════════════════╗
║      🏠 IDEALISTA BOT — Madrid Colocation       ║
║  3 chambres · Meublé · Max 2400€ · Castellana   ║
╠══════════════════════════════════════════════════╣
║  {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^48s} ║
╚══════════════════════════════════════════════════╝
""")

    # Import ici pour éviter de charger Selenium si --reset
    from scraper import run_scraper
    from emailer import send_email

    # 1. Scraping
    new_listings = run_scraper()

    # 2. Résumé console
    if new_listings:
        print(f"\n{'─'*50}")
        print(f"  🆕 {len(new_listings)} NOUVELLES ANNONCES")
        print(f"{'─'*50}")
        for i, l in enumerate(new_listings, 1):
            print(f"\n  #{i} {l.title}")
            print(f"      {l.summary()}")
            print(f"      🔗 {l.url}")
        print(f"\n{'─'*50}")
    else:
        print("\n  😴 Aucune nouvelle annonce aujourd'hui.\n")

    # 3. Email
    if not args.dry_run:
        send_email(new_listings, send_if_empty=args.force)
    else:
        print("  📋 Mode dry-run — pas d'email envoyé")

    # 4. Log
    os.makedirs(DATA_DIR, exist_ok=True)
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "new_count": len(new_listings),
        "status": "success",
    }
    log_file = f"{DATA_DIR}/runs.log"
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"\n✅ Terminé — {len(new_listings)} nouvelles annonces trouvées")


if __name__ == "__main__":
    main()
