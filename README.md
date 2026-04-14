# DentaMap — Diagnostic Tool (Cloud Edition)

## What this is
A cloud-hosted diagnostic exam tool for dental practices. Accessible from any browser, any device.

**URL:** `https://<project>.deta.dev`

## Features
- ✅ Comprehensive diagnostic grid (Biomechanical, Functional, Periodontal, Dentofacial)
- ✅ Optional Implant Risk Assessment (bone volume, density, systemic health, bruxism, healing)
- ✅ Radar chart results visualization
- ✅ Print-friendly results
- ✅ Exam history
- ✅ Staff login (password-protected)
- ✅ SQLite database (auto-persists on Deta servers)
- ✅ HTTPS everywhere

## Deploy

**Prerequisites:**
- Free account at [deta.sh](https://deta.sh)
- Deta CLI: `curl -fsSL https://install.deta.space | bash`
- Login: `deta login`

**Deploy:**
```bash
cd dentamap
chmod +x deploy.sh
./deploy.sh
```

You'll be prompted for:
- `Deta Project Name` — create one at deta.sh (e.g. `rdc` or `radiant`)
- `Staff Password` — your chosen login password

**After deploy:**
```
https://<project>.deta.dev
Login: admin / <your-password>
```

## First login — change the password
```bash
curl -s -X POST "https://<project>.deta.dev/api/auth/change-password" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <your-secret>" \
    -d '{"username":"admin","old_password":"<your-secret>","new_password":"<new-password>"}'
```

Or ask me and I'll run it for you.

## Staff workflow
1. Go to `https://<project>.deta.dev`
2. Log in
3. Click **Start New Exam**
4. Enter patient name (optional chart number)
5. Toggle **Implant Risk Assessment** if needed
6. Complete all 4 categories (6 questions each, 1-5 Likert scale)
7. Add optional clinician notes
8. View results — print or start new exam

## API
```
GET  /api/questions          — list all questions
POST /api/exam               — submit exam (auth required)
GET  /api/exams              — list past exams (auth required)
GET  /api/exam/{exam_id}     — fetch single exam (auth required)
POST /api/auth/login         — login
POST /api/auth/change-password — change password
```

Auth: `Authorization: Bearer <KOIS_SECRET>` header.

## Security notes
- Keep KOIS_SECRET safe — it's your API bearer token
- Change password after first login
- For full HIPAA compliance: add encryption at rest, BAA with Deta
- HTTPS enforced on all routes

## Cost
**$0** — Deta free tier.

## Troubleshooting
```bash
# View logs
deta micro logs dentamap --project <project>

# Restart
deta micro stop dentamap --project <project>
deta micro start dentamap --project <project>

# Health check
curl https://<project>.deta.dev/health
```
