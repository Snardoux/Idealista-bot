"""
Scraper Idealista v2 — utilise undetected-chromedriver + comportement humain
pour contourner la détection anti-bot et les CAPTCHAs.

Stratégie :
  1. Lance Chrome avec undetected-chromedriver (patche les signaux webdriver)
  2. Visite d'abord google.es (referrer naturel)
  3. Navigue vers Idealista via la barre d'adresse
  4. Accepte les cookies
  5. Scrolle naturellement avant d'extraire les données
  6. Pauses aléatoires entre chaque action
"""

import json
import os
import random
import re
import time
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
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
    price: int
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
    first_seen: str

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
def create_driver() -> uc.Chrome:
    """
    Crée un navigateur Chrome avec undetected-chromedriver.
    Patche automatiquement les propriétés navigator.webdriver,
    les signatures CDP, et les fingerprints Canvas/WebGL.
    """
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=es-ES,es")

    # En CI (GitHub Actions), on force headless
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        options.add_argument("--headless=new")

    driver = uc.Chrome(options=options, version_main=None)
    driver.set_page_load_timeout(30)

    return driver


# ─── COMPORTEMENT HUMAIN ─────────────────────────────────────────────
def human_delay(min_s: float = 1.0, max_s: float = 3.0):
    """Pause aléatoire simulant un humain."""
    time.sleep(random.uniform(min_s, max_s))


def human_scroll(driver, steps: int = 3):
    """Scrolle la page progressivement comme un humain."""
    for _ in range(steps):
        scroll_amount = random.randint(200, 500)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.5, 1.5))


def accept_cookies(driver):
    """Clique sur le bouton d'acceptation des cookies si présent."""
    cookie_selectors = [
        "#didomi-notice-agree-button",
        "button[id*='accept']",
        "button[class*='accept']",
        "button[id*='cookie']",
        ".didomi-continue-without-agreeing",
    ]
    for selector in cookie_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, selector)
            if btn.is_displayed():
                human_delay(0.5, 1.5)
                btn.click()
                print("  🍪 Cookies acceptés")
                human_delay(1, 2)
                return True
        except (NoSuchElementException, WebDriverException):
            continue
    return False


def warm_up_session(driver):
    """
    Visite google.es d'abord pour établir un historique de navigation
    naturel avec un referrer crédible.
    """
    print("  🌐 Warm-up: visite google.es...")
    try:
        driver.get("https://www.google.es")
        human_delay(2, 4)

        # Accepter les cookies Google si demandé
        try:
            google_accept = driver.find_element(By.ID, "L2AGLb")
            google_accept.click()
            human_delay(1, 2)
        except (NoSuchElementException, WebDriverException):
            pass

    except Exception as e:
        print(f"  ⚠️  Warm-up Google échoué (pas grave): {e}")


# ─── SCRAPING ────────────────────────────────────────────────────────
def _parse_price(text: str) -> Optional[int]:
    text = text.replace("\xa0", " ").strip()
    match = re.search(r"([\d.]+)\s*€", text)
    if match:
        return int(match.group(1).replace(".", ""))
    return None


def _parse_int(text: str) -> Optional[int]:
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def check_for_captcha(driver) -> bool:
    page = driver.page_source.lower()
    indicators = ["captcha", "robot", "verificar", "challenge", "recaptcha", "access denied"]
    return any(ind in page for ind in indicators)


def scrape_page(driver: uc.Chrome, url: str, is_first: bool = False) -> list[dict]:
    """Scrape une page de résultats Idealista."""
    print(f"  📄 Chargement: ...{url[-60:]}")

    driver.get(url)
    human_delay(3, 6)

    if is_first:
        accept_cookies(driver)

    # Vérifier CAPTCHA
    if check_for_captcha(driver):
        print("  ⚠️  CAPTCHA détecté ! Attente longue + retry...")
        human_delay(15, 30)
        human_scroll(driver, 2)
        human_delay(5, 10)
        driver.refresh()
        human_delay(5, 8)

        if check_for_captcha(driver):
            print("  ❌ CAPTCHA persistant — page skippée")
            # Debug : sauvegarder le HTML
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(f"{DATA_DIR}/debug_captcha.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return []
        print("  ✅ CAPTCHA résolu !")

    # Scroller pour charger le lazy-loading
    human_scroll(driver, 4)
    human_delay(1, 2)
    driver.execute_script("window.scrollTo(0, 0);")
    human_delay(1, 2)

    # Attendre les annonces
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article.item"))
        )
    except TimeoutException:
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".item-info-container, .listing-item")
                )
            )
        except TimeoutException:
            print("  ❌ Aucune annonce trouvée sur cette page")
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(f"{DATA_DIR}/debug_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("  📝 HTML sauvegardé dans data/debug_page.html")
            return []

    articles = driver.find_elements(By.CSS_SELECTOR, "article.item")
    if not articles:
        articles = driver.find_elements(By.CSS_SELECTOR, ".item-info-container")

    results = []

    for article in articles:
        try:
            raw = {}

            raw["id"] = (
                article.get_attribute("data-adid")
                or article.get_attribute("data-element-id")
                or article.get_attribute("id")
                or ""
            )

            try:
                link_el = article.find_element(By.CSS_SELECTOR, "a.item-link")
                raw["title"] = link_el.text.strip()
                raw["url"] = link_el.get_attribute("href") or ""
                if raw["url"] and not raw["url"].startswith("http"):
                    raw["url"] = "https://www.idealista.com" + raw["url"]
            except NoSuchElementException:
                try:
                    link_el = article.find_element(By.CSS_SELECTOR, "a[href*='/inmueble/']")
                    raw["title"] = link_el.text.strip()
                    raw["url"] = link_el.get_attribute("href") or ""
                except NoSuchElementException:
                    raw["title"] = ""
                    raw["url"] = ""

            try:
                price_el = article.find_element(By.CSS_SELECTOR, ".item-price, .price-row")
                raw["price_text"] = price_el.text.strip()
            except NoSuchElementException:
                raw["price_text"] = ""

            try:
                details_el = article.find_element(
                    By.CSS_SELECTOR, ".item-detail-char, .item-detail"
                )
                raw["details_text"] = details_el.text.strip()
            except NoSuchElementException:
                raw["details_text"] = ""

            try:
                desc_el = article.find_element(
                    By.CSS_SELECTOR, ".item-description, .ellipsis"
                )
                raw["description"] = desc_el.text.strip()
            except NoSuchElementException:
                raw["description"] = ""

            try:
                img_el = article.find_element(By.CSS_SELECTOR, "img")
                raw["image_url"] = (
                    img_el.get_attribute("src")
                    or img_el.get_attribute("data-src")
                    or img_el.get_attribute("data-ondemand-img")
                    or ""
                )
            except NoSuchElementException:
                raw["image_url"] = ""

            try:
                tags = article.find_elements(
                    By.CSS_SELECTOR, ".item-tags span, .item-highlight, .listing-tags span"
                )
                raw["tags"] = [t.text.strip().lower() for t in tags if t.text.strip()]
            except NoSuchElementException:
                raw["tags"] = []

            if raw.get("url") or raw.get("title"):
                results.append(raw)

        except Exception as e:
            print(f"  ⚠️  Erreur parsing annonce: {e}")
            continue

    print(f"  ✅ {len(results)} annonces extraites")
    return results


def raw_to_listing(raw: dict) -> Optional[Listing]:
    if not raw.get("id") and not raw.get("url"):
        return None

    listing_id = raw.get("id") or raw.get("url", "").rstrip("/").split("/")[-1]
    price = _parse_price(raw.get("price_text", ""))

    details = raw.get("details_text", "")
    rooms = None
    size = None
    floor = None

    for part in details.replace("·", "\n").split("\n"):
        part_lower = part.strip().lower()
        if "hab" in part_lower or "dorm" in part_lower:
            rooms = _parse_int(part)
        elif "m²" in part_lower or "m2" in part_lower:
            size = _parse_int(part)
        elif any(kw in part_lower for kw in ["planta", "bajo", "ático", "entresuelo"]):
            floor = part.strip()

    url = raw.get("url", "")
    district = ""
    url_parts = url.replace("https://www.idealista.com", "").split("/")
    if len(url_parts) > 2:
        district = url_parts[2] if "madrid" not in url_parts[2] else ""

    tags_text = " ".join(raw.get("tags", []))
    desc_lower = raw.get("description", "").lower()
    combined = tags_text + " " + desc_lower

    is_furnished = any(kw in combined for kw in ["amueblado", "amueblada", "meublé", "furnished"])
    has_elevator = any(kw in combined for kw in ["ascensor", "elevator", "ascenseur"])
    has_ac = any(kw in combined for kw in ["aire acondicionado", "climatización", "clim"])

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
    filters = SEARCH_CONFIG["filters"]
    filtered = []
    for listing in listings:
        if listing.price > 0 and listing.price > filters["max_price"]:
            continue
        if listing.rooms and listing.rooms < filters["min_rooms"]:
            continue
        filtered.append(listing)
    return filtered


# ─── GESTION DES ANNONCES DÉJÀ VUES ─────────────────────────────────
def load_seen_ids() -> set[str]:
    if not os.path.exists(SEEN_LISTINGS_FILE):
        return set()
    with open(SEEN_LISTINGS_FILE, "r") as f:
        data = json.load(f)
    return set(data.get("seen_ids", []))


def save_seen_ids(seen_ids: set[str]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SEEN_LISTINGS_FILE, "w") as f:
        json.dump(
            {"seen_ids": list(seen_ids), "last_update": datetime.now(timezone.utc).isoformat()},
            f, indent=2,
        )


def save_history(listings: list[Listing]):
    os.makedirs(DATA_DIR, exist_ok=True)
    history_file = f"{DATA_DIR}/history.json"
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            history = json.load(f)
    for listing in listings:
        history.append(asdict(listing))
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


# ─── ORCHESTRATION PRINCIPALE ────────────────────────────────────────
def run_scraper() -> list[Listing]:
    print("🚀 Démarrage du scraper Idealista v2 (undetected-chromedriver)...")
    print(f"   URL: {SEARCH_CONFIG['base_url']}")

    os.makedirs(DATA_DIR, exist_ok=True)
    driver = create_driver()
    all_raw = []

    try:
        warm_up_session(driver)

        results = scrape_page(driver, SEARCH_CONFIG["base_url"], is_first=True)
        all_raw.extend(results)

        for page_num in range(2, SEARCH_CONFIG["max_pages"] + 1):
            if not results:
                print(f"  ℹ️  Page précédente vide, arrêt pagination")
                break

            wait = random.uniform(8, 15)
            print(f"  ⏳ Pause {wait:.0f}s avant page {page_num}...")
            time.sleep(wait)

            separator = "&" if "?" in SEARCH_CONFIG["base_url"] else "?"
            page_url = f"{SEARCH_CONFIG['base_url']}{separator}pagina={page_num}"
            results = scrape_page(driver, page_url)
            all_raw.extend(results)

    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print(f"\n📊 {len(all_raw)} annonces brutes récupérées")
    listings = [raw_to_listing(r) for r in all_raw]
    listings = [l for l in listings if l is not None]
    print(f"   {len(listings)} annonces parsées")

    listings = apply_filters(listings)
    print(f"   {len(listings)} après filtrage critères")

    seen_in_batch = set()
    unique = []
    for l in listings:
        if l.id not in seen_in_batch:
            seen_in_batch.add(l.id)
            unique.append(l)
    listings = unique
    print(f"   {len(listings)} après déduplication")

    seen_ids = load_seen_ids()
    new_listings = [l for l in listings if l.id not in seen_ids]
    print(f"   🆕 {len(new_listings)} NOUVELLES annonces !")

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
