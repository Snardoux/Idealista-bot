# 🏠 Idealista Bot — Alertes Location Madrid

Bot automatisé qui scanne **idealista.com** chaque matin et t'envoie par email les nouvelles annonces correspondant à tes critères.

## 🎯 Critères configurés

| Critère | Valeur |
|---------|--------|
| Type | Location meublée |
| Ville | Madrid |
| Budget max | 2 400€/mois (800€/personne × 3) |
| Chambres | 3 minimum |
| Proximité | ≤20 min à pied / ≤40 min transports de Paseo de la Castellana 93 |

## ⚡ Démarrage rapide

### 1. Cloner le repo

```bash
git clone https://github.com/TON-USER/idealista-bot.git
cd idealista-bot
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

> **Note** : Chrome ou Chromium doit être installé sur ta machine.

### 3. Configurer l'email

#### Option A — Variables d'environnement (recommandé)

```bash
export IDEALISTA_EMAIL="tonemail@gmail.com"
export IDEALISTA_PASSWORD="abcd efgh ijkl mnop"  # App Password Gmail
export IDEALISTA_RECIPIENTS="toi@gmail.com,coloc1@gmail.com,coloc2@gmail.com"
```

#### Option B — Directement dans `config.py`

Remplis les champs `sender_email`, `sender_password`, et `recipients`.

### 4. Créer un App Password Gmail

1. Va sur [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Sélectionne **"Mail"** et **"Autre"** → nomme-le "Idealista Bot"
3. Copie le mot de passe à 16 caractères généré
4. C'est CE mot de passe qu'il faut utiliser (pas ton mdp Gmail normal)

> ⚠️ La vérification en 2 étapes doit être activée sur ton compte Google.

### 5. Lancer

```bash
# Scrape + email si nouvelles annonces
python main.py

# Test sans envoyer d'email
python main.py --dry-run

# Forcer l'envoi même sans nouvelles annonces
python main.py --force

# Remettre à zéro les annonces déjà vues
python main.py --reset
```

## 🤖 Automatisation quotidienne (GitHub Actions)

Le bot se lance **automatiquement chaque matin à 7h30 (heure de Madrid)** via GitHub Actions.

### Setup

1. **Push** le repo sur GitHub

2. **Ajouter les secrets** dans GitHub :
   - Repo → Settings → Secrets and variables → Actions → New repository secret
   - Ajouter :
     - `SENDER_EMAIL` → ton email Gmail
     - `SENDER_PASSWORD` → ton App Password Gmail
     - `RECIPIENTS` → emails séparés par des virgules

3. **C'est tout !** Le workflow `.github/workflows/daily_scan.yml` fera le reste.

4. Pour lancer manuellement : Actions → "Idealista Daily Scan" → Run workflow

## 📁 Structure du projet

```
idealista-bot/
├── main.py              # Point d'entrée principal
├── scraper.py           # Scraping Selenium + parsing
├── emailer.py           # Génération HTML + envoi SMTP
├── config.py            # Tous les paramètres
├── requirements.txt     # Dépendances Python
├── .github/
│   └── workflows/
│       └── daily_scan.yml   # Automatisation quotidienne
└── data/                    # (auto-généré)
    ├── seen_listings.json   # IDs déjà envoyés
    ├── history.json         # Historique complet
    └── runs.log             # Log des exécutions
```

## ⚙️ Personnalisation

### Modifier les critères

Tout se passe dans `config.py` :
- `SEARCH_CONFIG["base_url"]` → URL de recherche Idealista (modifiable via le site)
- `SEARCH_CONFIG["filters"]` → filtres post-scraping
- `SEARCH_CONFIG["max_pages"]` → nombre de pages scannées
- `NEARBY_DISTRICTS` → quartiers acceptés

### Changer l'heure d'envoi

Dans `.github/workflows/daily_scan.yml`, modifie le cron :
```yaml
- cron: '30 5 * * *'  # 5h30 UTC = 7h30 Madrid (été)
```

## ⚠️ Avertissements

- **Idealista détecte les bots** : le scraper utilise des techniques d'évasion (user-agent aléatoire, délais, masquage webdriver) mais des CAPTCHAs peuvent apparaître
- **Respecte les CGU** : cet outil est pour un usage personnel de veille immobilière
- **Rate limiting** : ne lance pas le bot trop souvent (1×/jour suffit)
- Si le bot est bloqué, attends 24h ou change d'IP

## 🛠️ Dépannage

| Problème | Solution |
|----------|----------|
| CAPTCHA détecté | Attendre 24h, le bot retry automatiquement |
| 0 annonces trouvées | Vérifier l'URL dans `config.py` en l'ouvrant dans un navigateur |
| Email non reçu | Vérifier App Password et que le 2FA est activé |
| Chrome pas trouvé | `apt install chromium-browser` ou `brew install --cask google-chrome` |
