#!/usr/bin/env bash
# ──────────────────────────────────────────
# DentaMap — Diagnostic Tool Deploy Script
# Radiant Dental Care | Dr. Jay Siddiqui
# ──────────────────────────────────────────
set -e
cd "$(dirname "$0")"

echo "⏳ Checking Deta CLI..."
if ! command -v deta &>/dev/null; then
    echo "Installing Deta CLI..."
    curl -fsSL https://install.deta.space | bash
fi

echo ""
read -p "Deta Project Name (create at https://deta.sh first): " PROJECT
if [ -z "$PROJECT" ]; then echo "Aborted."; exit 1; fi

read -p "Staff Password (staff will use this to log in): " SECRET
if [ -z "$SECRET" ]; then echo "Aborted."; exit 1; fi

echo ""
echo "🔐 Setting env vars..."
deta env set KOIS_SECRET="$SECRET" --project "$PROJECT"

echo ""
echo "🚀 Deploying..."
deta deploy --project "$PROJECT"

echo ""
echo "✅ DentaMap is LIVE!"
echo "   Staff URL: https://${PROJECT}.deta.dev"
echo "   API URL:   https://${PROJECT}.deta.dev/api"
echo "   Default login: admin / $SECRET"
echo ""
echo "⚠️  Change the admin password after first login:"
echo "   curl -X POST https://${PROJECT}.deta.dev/api/auth/change-password \"
echo "   -H 'Content-Type: application/json' \"
echo "   -H 'Authorization: Bearer $SECRET' \"
echo "   -d '{\"username\":\"admin\",\"old_password\":\"$SECRET\",\"new_password\":\"YOUR_NEW_PASSWORD\"}'"
