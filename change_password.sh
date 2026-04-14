#!/usr/bin/env bash
# Change DentaMap admin password via API
PROJECT="${1:-}"

if [ -z "$PROJECT" ]; then
    echo "Usage: ./change_password.sh <project> <current_secret>"
    echo "Example: ./change_password.sh radiant MySecret123"
    exit 1
fi

SECRET="${2:-}"
if [ -z "$SECRET" ]; then
    echo "Usage: ./change_password.sh <project> <current_secret>"
    exit 1
fi

read -p "New password: " NEW_PW

curl -s -X POST "https://${PROJECT}.deta.dev/api/auth/change-password" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $SECRET" \
    -d "{\"username\":\"admin\",\"old_password\":\"$SECRET\",\"new_password\":\"$NEW_PW\"}"
