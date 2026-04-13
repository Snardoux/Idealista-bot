#!/bin/bash
# ─────────────────────────────────────────────────────────────
# 🏠 Setup automatisation locale (macOS)
# Lance le bot chaque matin à 7h30 depuis ton Mac.
#
# Avantage : ton IP résidentielle n'est PAS blacklistée 
# par Idealista (contrairement aux IPs GitHub Actions).
#
# Usage : chmod +x setup_local_cron.sh && ./setup_local_cron.sh
# ─────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH="$(which python3)"
PLIST_NAME="com.idealista.bot"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
LOG_DIR="$SCRIPT_DIR/data/logs"

echo "🏠 Configuration du bot Idealista en local"
echo "   Dossier : $SCRIPT_DIR"
echo "   Python  : $PYTHON_PATH"
echo ""

# 1. Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 non trouvé. Installe-le : brew install python@3.12"
    exit 1
fi

# 2. Installer les dépendances
echo "📦 Installation des dépendances..."
pip3 install -r "$SCRIPT_DIR/requirements.txt" --quiet

# 3. Créer le dossier de logs
mkdir -p "$LOG_DIR"

# 4. Créer le script wrapper
cat > "$SCRIPT_DIR/run_bot.sh" << 'WRAPPER'
#!/bin/bash
cd "$(dirname "$0")"
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

LOGFILE="data/logs/bot_$(date +%Y%m%d_%H%M%S).log"
mkdir -p data/logs

echo "=== Idealista Bot — $(date) ===" >> "$LOGFILE"
python3 main.py >> "$LOGFILE" 2>&1
echo "=== Terminé — $(date) ===" >> "$LOGFILE"

# Garder seulement les 30 derniers logs
ls -t data/logs/bot_*.log 2>/dev/null | tail -n +31 | xargs rm -f 2>/dev/null
WRAPPER
chmod +x "$SCRIPT_DIR/run_bot.sh"

# 5. Créer le LaunchAgent (équivalent macOS de cron)
cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${SCRIPT_DIR}/run_bot.sh</string>
    </array>

    <!-- Chaque jour à 7h30 -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>

    <!-- Logs système -->
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/launchd_stderr.log</string>

    <!-- Lancer même si le Mac était en veille à l'heure prévue -->
    <key>StartInterval</key>
    <integer>86400</integer>
</dict>
</plist>
PLIST

# 6. Charger le LaunchAgent
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo ""
echo "✅ Bot configuré ! Il se lancera chaque jour à 7h30."
echo ""
echo "   Commandes utiles :"
echo "   ─────────────────────────────────────────────"
echo "   Lancer maintenant  : ./run_bot.sh"
echo "   Voir les logs      : cat data/logs/bot_*.log"
echo "   Désactiver le bot  : launchctl unload $PLIST_PATH"
echo "   Réactiver le bot   : launchctl load $PLIST_PATH"
echo "   Supprimer le bot   : launchctl unload $PLIST_PATH && rm $PLIST_PATH"
echo ""
echo "   ⚠️  Le Mac doit être allumé (pas forcément déverrouillé)"
echo "      à 7h30 pour que le bot se lance."
