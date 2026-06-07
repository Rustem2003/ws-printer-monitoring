<div align="center">

<img src="frontend/public/logo.svg" alt="WS Printer Monitoring" width="120" />

# WS Printer Monitoring

**Enterprise printer & MFP monitoring system with auto-discovery, SNMP polling, Telegram notifications and admin web panel.**

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Material-UI](https://img.shields.io/badge/MUI-6-007FFF?logo=mui&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

🇬🇧 **English** · [🇷🇺 Русский](README.md)

[Features](#-features) ·
[Architecture](#-architecture) ·
[Installation](#-3-command-install) ·
[API](#-rest-api) ·
[Support](#-support-the-project)

</div>

---

## ✨ Features

- 🔍 **Auto-discovery** of printers in local network (Ping Sweep + SNMP probe + Nmap)
- 📊 **SNMP polling** v1 / v2c / v3 — device status, CMYK toner levels, page counters, serial number, firmware, errors
- 🖨 **8 vendors**: HP, Xerox, **Canon (MF/iR — v1, ADV — v1)**, Brother, Kyocera, Ricoh, Konica Minolta, Epson
- 🔔 **Telegram notifications** with per-event-type **custom repeat intervals** (once / every 5 min / 15 min / 1 h / 1 day / any value)
- 📱 **Web panel** with React 19 + MUI 6 — dark/light themes, **3 languages (RU / KK / EN)**
- 📈 **Dashboard** with live analytics: online/offline, errors in last 24h, consumables to replace, **6 charts** (Recharts)
- 🛠 **UI-driven management**: manual printer add, custom subnet scan, room/location, **hot-reload bot token without restart**
- 🔐 **JWT auth + RBAC**: Super Admin / Administrator / Operator / Viewer
- 🐳 **Full containerization** via Docker Compose (9 services)
- 🔄 **WebSocket realtime** updates
- 🌐 **REST API** with Swagger UI — ready for 1С, CRM, Service Desk, Zabbix, Grafana integrations

---

## 🏗 Architecture

### Services (9 containers)

| Service | Tech | Port |
|---|---|---|
| `postgres` | PostgreSQL 16 Alpine | 5432 |
| `redis` | Redis 7 Alpine (AOF) | 6379 |
| `backend` | FastAPI + uvicorn (Python 3.12) | 8000 |
| `websocket` | FastAPI WebSocket realtime | 8888 |
| `monitoring-service` | asyncio + pysnmp + ping | 9000 |
| `discovery-service` | FastAPI + nmap + SNMP (`network_mode: host`) | 9001 |
| `notification-service` | FastAPI + Telegram Bot API | 9002 |
| `frontend` | React 19 + Vite + MUI 6 → nginx | 8080 |
| `nginx` | Reverse proxy (optional) | 8081 |

### Data flow

```
monitoring (9000) ──ping+SNMP──► printers
   │ POST status                              ┐
   │ POST events ───► notification (9002) ────┤ Telegram Bot API
   ▼                                          │
backend (8000) ◄── REST /api/v1/* ── frontend (8080)
   │                                  ▲
   ├─► postgres (5432)                │
   ├─► redis (6379) ── pub/sub ── websocket (8888) ── realtime UI
   ▼
discovery (9001, host net) ── discover ─► backend (new printers)
```

---

## 🚀 3-command install

### Requirements

- Linux (Ubuntu 22.04+ / Debian 12+ / RHEL 9+) or macOS
- Docker 24+ and Docker Compose v2
- 4 GB RAM (8 GB recommended), 20 GB disk
- Access to the network where printers live (for SNMP)

### Run

```bash
git clone https://github.com/Rustem2003/ws-printer-monitoring.git
cd ws-printer-monitoring
./install.sh
```

The installer asks for the server IP, generates random secrets and starts Docker Compose.

### Access

| What | URL |
|---|---|
| 🖥 Web panel | `http://<SERVER_IP>:8080` |
| 📘 Swagger API | `http://<SERVER_IP>:8000/docs` |

**Default credentials:** `admin` / `admin123` (change immediately after login!)

---

## 🔧 First-time UI setup

1. **Sign in** (`admin` / `admin123`)
2. Open **«Telegram bot»** in the menu → paste the token from `@BotFather` + chat_id → click **«Verify token (getMe)»**
3. Open **«Printers»** → enter your subnet (e.g. `192.168.0.0/24`) → **«Scan»**
4. For Canon MF/iR — click ✏ «Edit» → switch SNMP version to **`1`**
5. Assign a **Room/location** to each printer
6. Open **«Notification period»** — tune repeat interval for every event type
7. Watch the **Dashboard** — data refreshes automatically every 30 seconds

---

## 🌐 SNMP version cheatsheet by vendor

| Vendor / series | SNMP version | Note |
|---|---|---|
| **Canon** MF, LBP, iR, iR-ADV | **v1** | v1 only, **not v2c** |
| HP LaserJet, OfficeJet | v2c | |
| Xerox WorkCentre, Phaser, VersaLink | v2c | |
| Brother HL, MFC | v2c | |
| Kyocera ECOSYS | v2c | |
| Ricoh Aficio | v2c | |
| Konica Minolta Bizhub | v2c | |
| Epson WorkForce | v2c | |

If a newly-added printer shows **offline** while ping works — almost always the
SNMP version is wrong. Switch it via UI ✏ «Edit».

---

## 📦 Operations

```bash
# Status
docker compose ps

# Logs
docker compose logs -f backend
docker compose logs -f monitoring-service

# Restart / update
docker compose restart
docker compose up -d --build

# Database backup
docker compose exec postgres pg_dump -U printer printerdb | gzip > backup-$(date +%F).sql.gz

# Stop (data preserved)
docker compose down

# Stop and wipe volumes (⚠️ deletes the DB!)
docker compose down -v
```

---

## 🔌 REST API

Full docs at: `http://<SERVER>:8000/docs` (Swagger UI).

```http
POST   /api/v1/auth/login                          # JWT login
GET    /api/v1/printers                            # List
POST   /api/v1/printers                            # Add manually
PUT    /api/v1/printers/{id}                       # Update (snmp_version, location, vendor, ...)
DELETE /api/v1/printers/{id}
POST   /api/v1/printers/{id}/check                 # On-demand SNMP probe
GET    /api/v1/printers/{id}/consumables
GET    /api/v1/events                              # JOIN to printers (name, IP, location)
GET    /api/v1/statistics                          # Overview
GET    /api/v1/statistics/charts                   # Aggregates for dashboard charts
POST   /api/v1/discovery/start                     # {subnet, method}
GET    /api/v1/telegram-chats                      # CRUD chats
POST   /api/v1/telegram-chats/{id}/test            # Send test message
GET    /api/v1/notification-settings               # Repeat period per event type
PUT    /api/v1/notification-settings/{event_type}
GET    /api/v1/system-settings/telegram            # Bot token (masked)
PUT    /api/v1/system-settings/telegram            # Hot-reload token without restart
POST   /api/v1/system-settings/telegram/test       # getMe
```

---

## 📁 Project layout

```
ws-printer-monitoring/
├── docker-compose.yml          # 9 services
├── .env.example                # Env template
├── install.sh                  # Auto-installer
├── README.md                   # Russian (default)
├── README.en.md                # This file (English)
├── LICENSE                     # MIT
│
├── backend/                    # FastAPI (Python 3.12)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── migrations/init.sql
│   └── app/
│       ├── main.py
│       ├── core/               # config, database, auth (JWT + bcrypt)
│       ├── models/             # 13 SQLAlchemy models
│       ├── routers/            # auth, printers, events, discovery, statistics,
│       │                       # telegram, notification_settings, system_settings
│       └── schemas/            # Pydantic
│
├── monitoring/                 # SNMP/Ping collector + on-demand HTTP API
├── discovery/                  # Auto-discovery (Nmap + SNMP probe)
├── notification/               # Telegram bot (multi-chat, throttle, CMYK + location in message)
├── frontend/                   # React 19 + Vite + MUI 6 + Recharts
│   ├── public/logo.svg
│   └── src/
│       ├── i18n.tsx            # RU / KK / EN (200+ keys)
│       ├── api.ts              # axios + JWT interceptor
│       ├── pages/              # Dashboard, Printers, Events, Telegram,
│       │                       # BotSettings, NotificationSettings, Login
│       └── components/         # Shell, Footer
└── nginx/                      # Reverse proxy
```

---

## 🩺 Troubleshooting

<details>
<summary><b>Printer shows offline but ping works</b></summary>

Most likely SNMP version mismatch. Click ✏ «Edit» on the printer →
SNMP version → **`1`** for Canon MF/iR, `2c` for the rest.
</details>

<details>
<summary><b>Telegram doesn't deliver messages</b></summary>

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"
```
Should return `{"ok":true,"result":{...}}`. If `401` — the token is invalid,
get a fresh one from `@BotFather`.
</details>

<details>
<summary><b>Discovery finds nothing</b></summary>

Discovery runs in `network_mode: host` — Docker must have access to the local
network. Verify:
```bash
docker compose exec discovery-service ping -c 2 192.168.0.1
docker compose exec discovery-service snmpget -v2c -c public 192.168.0.X 1.3.6.1.2.1.1.1.0
```
</details>

<details>
<summary><b>Backend crashes with <code>bcrypt password longer than 72 bytes</code></b></summary>

`passlib` is incompatible with newer `bcrypt`. The repo pins `bcrypt==3.2.2`
in `backend/requirements.txt`. Rebuild:
```bash
docker compose up -d --build backend
```
</details>

---

## 🛡 Security

- 🔑 JWT authentication for all protected endpoints
- 🔒 bcrypt password hashing
- 🚪 Internal token for service-to-service requests (monitoring/discovery → backend)
- 🛡 Telegram token is masked in the API (`896***:AAGY***2z1Y`)
- 📋 Audit logs (`audit_logs` table)
- 🌐 CORS configurable
- 🔐 All secrets via `.env` (never committed)

---

## 🗺 Roadmap

- [ ] WebSocket push of events to UI without polling
- [ ] Reports export to Excel and PDF
- [ ] SAML / LDAP / OAuth2 SSO
- [ ] Multi-tenant with strict organization isolation
- [ ] Mobile app (React Native / Flutter)
- [ ] Email notifications (SMTP)
- [ ] WhatsApp / Slack integration
- [ ] Prometheus / Grafana metrics exporter

---

## 🤝 Contributing

Pull requests are welcome! For major changes please open an issue first to
discuss the direction.

```bash
git clone https://github.com/Rustem2003/ws-printer-monitoring.git
cd ws-printer-monitoring
git checkout -b feature/my-feature
# ... your changes ...
git commit -m "feat: add my-feature"
git push origin feature/my-feature
# open a PR on GitHub
```

---

## 📞 Support the project

**Developer:** ИП WEB-Soft (Kazakhstan)
**Email:** [info@web-soft.kz](mailto:info@web-soft.kz)

If this project helps your business — please consider supporting development:

💳 **IBAN:** `KZ48722S000035656178`

---

## 📄 License

[MIT License](LICENSE) © 2026 ИП WEB-Soft

---

<div align="center">

⭐ **Like the project? Give it a star on GitHub!** ⭐

</div>
