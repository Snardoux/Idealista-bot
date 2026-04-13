"""
Scraper Idealista — utilise Selenium (headless Chrome) pour contourner
les protections anti-bot du site.
"""

import json
import os
import random
import re
import time
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

from config import SEARCH_CONFIG, DATA_DIR, SEEN_LISTINGS_FILE


# ─── DATA MODEL ──────────────────────────────────────────────────────
@dataclass
class Listing:
    id: str
    title: str
    price: int                  # €/mois
    rooms: Optional[int]
    size_m2: Optional[int]
    floor: Optional[str]
    address: str
    district: str
    url: str
    image_url: Optional[str]
    description: str
    has_elevator: Optional[bool]
    has_ac: Optional[bool]
    is_furnished: bool
    first_seen: str             # ISO timestamp

    def summary(self) -> str:
        parts = [f"💰 {self.price}€/mois"]
        if self.rooms:
            parts.append(f"🛏 {self.rooms} ch.")
        if self.size_m2:
            parts.append(f"📐 {self.size_m2}m²")
        if self.floor:
            parts.append(f"🏢 {self.floor}")
        if self.has_elevator:
            parts.append("🛗 Ascenseur")
        if self.has_ac:
            parts.append("❄️ Clim")
        return " · ".join(parts)


# ─── BROWSER SETUP ───────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def create_driver() -> webdriver.Chrome:
    """Crée un navigateur Chrome headless configuré pour éviter la détection."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    options.add_argument("--lang=es-ES")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)

    # Masquer les propriétés webdriver
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.navigator.chrome = {runtime: {}};
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en']});
            """
        },
    )
    return driver


# ─── SCRAPING ────────────────────────────────────────────────────────
def _parse_price(text: str) -> Optional[int]:
    """Extrait le prix en euros depuis un texte comme '1.200 €/mes'."""
    match = re.search(r"([\d.]+)\s*€", text.replace(".", ""))
    if match:
        return int(match.group(1))
    # Format avec point comme séparateur de milliers
    match = re.search(r"([\d]+\.[\d]+)\s*€", text)
    if match:
        return int(match.group(1).replace(".", ""))
    return None


def _parse_int(text: str) -> Optional[int]:
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def scrape_page(driver: webdriver.Chrome, url: str) -> list[dict]:
    """Scrape une page de résultats Idealista et retourne les annonces brutes."""
    print(f"  📄 Chargement: {url}")
    driver.get(url)

    # Attente aléatoire pour simuler un humain
    time.sleep(random.uniform(3, 6))

    # Attendre que les annonces soient chargées
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article.item"))
        )
    except TimeoutException:
        # Vérifier si c'est un captcha
        if "captcha" in driver.page_source.lower():
            print("  ⚠️  CAPTCHA détecté ! Attente 30s puis retry...")
            time.sleep(30)
            driver.refresh()
            time.sleep(5)
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article.item"))
                )
            except TimeoutException:
                print("  ❌ Impossible de charger la page (captcha persistant)")
                return []
        else:
            print("  ❌ Timeout — aucune annonce trouvée sur cette page")
            return []

    articles = driver.find_elements(By.CSS_SELECTOR, "article.item")
    results = []

    for article in articles:
        try:
            raw = {}

            # ID unique
            raw["id"] = article.get_attribute("data-adid") or article.get_attribute("id") or ""

            # Titre et lien
            try:
                link_el = article.find_element(By.CSS_SELECTOR, "a.item-link")
                raw["title"] = link_el.text.strip()
                raw["url"] = link_el.get_attribute("href") or ""
                if raw["url"] and not raw["url"].startswith("http"):
                    raw["url"] = "https://www.idealista.com" + raw["url"]
            except NoSuchElementException:
                raw["title"] = ""
                raw["url"] = ""

            # Prix
            try:
                price_el = article.find_element(By.CSS_SELECTOR, ".item-price")
                raw["price_text"] = price_el.text.strip()
            except NoSuchElementException:
                raw["price_text"] = ""

            # Détails (chambres, m², étage)
            try:
                details_el = article.find_element(By.CSS_SELECTOR, ".item-detail-char")
                raw["details_text"] = details_el.text.strip()
            except NoSuchElementException:
                raw["details_text"] = ""

            # Description
            try:
                desc_el = article.find_element(By.CSS_SELECTOR, ".item-description")
                raw["description"] = desc_el.text.strip()
            except NoSuchElementException:
                raw["description"] = ""

            # Image
            try:
                img_el = article.find_element(By.CSS_SELECTOR, "img")
                raw["image_url"] = img_el.get_attribute("src") or img_el.get_attribute("data-src") or ""
            except NoSuchElementException:
                raw["image_url"] = ""

            # Tags (meublé, ascenseur, clim, etc.)
            try:
                tags = article.find_elements(By.CSS_SELECTOR, ".item-tags span, .item-highlight")
                raw["tags"] = [t.text.strip().lower() for t in tags]
            except NoSuchElementException:
                raw["tags"] = []

            results.append(raw)

        except Exception as e:
            print(f"  ⚠️  Erreur parsing annonce: {e}")
            continue

    print(f"  ✅ {len(results)} annonces extraites")
    return results


def raw_to_listing(raw: dict) -> Optional[Listing]:
    """Convertit les données brutes en objet Listing structuré."""
    if not raw.get("id") and not raw.get("url"):
        return None

    listing_id = raw.get("id") or raw.get("url", "").split("/")[-2]
    price = _parse_price(raw.get("price_text", ""))

    # Parser les détails
    details = raw.get("details_text", "")
    rooms = None
    size = None
    floor = None

    for part in details.split("\n"):
        part_lower = part.strip().lower()
        if "hab" in part_lower or "dorm" in part_lower:
            rooms = _parse_int(part)
        elif "m²" in part_lower or "m2" in part_lower:
            size = _parse_int(part)
        elif "planta" in part_lower or "piso" in part_lower or "bajo" in part_lower:
            floor = part.strip()

    # Déterminer le quartier depuis l'URL
    url = raw.get("url", "")
    district = ""
    url_parts = url.replace("https://www.idealista.com", "").split("/")
    if len(url_parts) > 2:
        district = url_parts[2] if "madrid" not in url_parts[2] else ""

    # Tags
    tags = raw.get("tags", [])
    tags_text = " ".join(tags)
    desc_lower = raw.get("description", "").lower()

    is_furnished = any(
        kw in tags_text or kw in desc_lower
        for kw in ["amueblado", "amueblada", "meublé", "furnished"]
    )
    has_elevator = any(
        kw in tags_text or kw in desc_lower
        for kw in ["ascensor", "elevator", "ascenseur"]
    )
    has_ac = any(
        kw in tags_text or kw in desc_lower
        for kw in ["aire acondicionado", "climatización", "clim"]
    )

    return Listing(
        id=str(listing_id),
        title=raw.get("title", "Sans titre"),
        price=price or 0,
        rooms=rooms,
        size_m2=size,
        floor=floor,
        address="",
        district=district,
        url=raw.get("url", ""),
        image_url=raw.get("image_url"),
        description=raw.get("description", "")[:500],
        has_elevator=has_elevator if has_elevator else None,
        has_ac=has_ac if has_ac else None,
        is_furnished=is_furnished,
        first_seen=datetime.now(timezone.utc).isoformat(),
    )


# ─── FILTRAGE ────────────────────────────────────────────────────────
def apply_filters(listings: list[Listing]) -> list[Listing]:
    """Applique les filtres de config.py sur les annonces."""
    filters = SEARCH_CONFIG["filters"]
    filtered = []

    for listing in listings:
        # Filtre prix
        if listing.price > 0 and listing.price > filters["max_price"]:
            continue
        # Filtre chambres
        if listing.rooms and listing.rooms < filters["min_rooms"]:
            continue
        # Filtre meublé (la recherche URL filtre déjà, mais double check)
        if filters["furnished_only"] and not listing.is_furnished:
            # On garde quand même si on n'a pas pu détecter le meublé
            # (le filtre URL s'en charge)
            pass

        filtered.append(listing)

    return filtered


# ─── GESTION DES ANNONCES DÉJÀ VUES ─────────────────────────────────
def load_seen_ids() -> set[str]:
    """Charge les IDs des annonces déjà envoyées."""
    if not os.path.exists(SEEN_LISTINGS_FILE):
        return set()
    with open(SEEN_LISTINGS_FILE, "r") as f:
        data = json.load(f)
    return set(data.get("seen_ids", []))


def save_seen_ids(seen_ids: set[str]):
    """Sauvegarde les IDs des annonces déjà envoyées."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SEEN_LISTINGS_FILE, "w") as f:
        json.dump({"seen_ids": list(seen_ids), "last_update": datetime.now(timezone.utc).isoformat()}, f, indent=2)


def save_history(listings: list[Listing]):
    """Ajoute les nouvelles annonces à l'historique."""
    os.makedirs(DATA_DIR, exist_ok=True)
    history = []
    if os.path.exists(SEEN_LISTINGS_FILE.replace("seen_listings", "history")):
        with open(SEEN_LISTINGS_FILE.replace("seen_listings", "history"), "r") as f:
            history = json.load(f)

    for listing in listings:
        history.append(asdict(listing))

    with open(SEEN_LISTINGS_FILE.replace("seen_listings", "history"), "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


# ─── ORCHESTRATION PRINCIPALE ────────────────────────────────────────
def run_scraper() -> list[Listing]:
    """
    Lance le scraping complet :
    1. Ouvre le navigateur
    2. Parcourt les pages de résultats
    3. Parse et filtre les annonces
    4. Identifie les nouvelles annonces
    5. Met à jour le fichier de suivi
    """
    print("🚀 Démarrage du scraper Idealista...")
    print(f"   URL: {SEARCH_CONFIG['base_url']}")

    driver = create_driver()
    all_raw = []

    try:
        # Page 1
        all_raw.extend(scrape_page(driver, SEARCH_CONFIG["base_url"]))

        # Pages suivantes
        for page_num in range(2, SEARCH_CONFIG["max_pages"] + 1):
            time.sleep(random.uniform(5, 10))  # Pause anti-détection
            separator = "&" if "?" in SEARCH_CONFIG["base_url"] else "?"
            page_url = f"{SEARCH_CONFIG['base_url']}{separator}pagina={page_num}"
            results = scrape_page(driver, page_url)
            if not results:
                print(f"  ℹ️  Pas de résultats page {page_num}, arrêt pagination")
                break
            all_raw.extend(results)

    finally:
        driver.quit()

    # Conversion et filtrage
    print(f"\n📊 {len(all_raw)} annonces brutes récupérées")
    listings = [raw_to_listing(r) for r in all_raw]
    listings = [l for l in listings if l is not None]
    print(f"   {len(listings)} annonces parsées")

    listings = apply_filters(listings)
    print(f"   {len(listings)} après filtrage critères")

    # Identifier les nouvelles
    seen_ids = load_seen_ids()
    new_listings = [l for l in listings if l.id not in seen_ids]
    print(f"   🆕 {len(new_listings)} NOUVELLES annonces !")

    # Sauvegarder
    if new_listings:
        new_ids = {l.id for l in new_listings}
        save_seen_ids(seen_ids | new_ids)
        save_history(new_listings)

    return new_listings


if __name__ == "__main__":
    new = run_scraper()
    if new:
        print("\n── Nouvelles annonces ──────────────────────────────")
        for l in new:
            print(f"\n  {l.title}")
            print(f"  {l.summary()}")
            print(f"  🔗 {l.url}")
    else:
        print("\n😴 Aucune nouvelle annonce aujourd'hui.")
