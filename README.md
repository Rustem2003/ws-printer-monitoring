<div align="center">

<img src="frontend/public/logo.svg" alt="WS Printer Monitoring" width="120" />

# WS Printer Monitoring

**Корпоративная система мониторинга принтеров и МФУ с автообнаружением, SNMP-опросом, Telegram-уведомлениями и веб-панелью администратора**

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Material-UI](https://img.shields.io/badge/MUI-6-007FFF?logo=mui&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

[Возможности](#-возможности) ·
[Архитектура](#-архитектура) ·
[Установка](#-установка-за-3-команды) ·
[API](#-rest-api) ·
[Поддержка](#-поддержка-проекта)

</div>

---

## ✨ Возможности

- 🔍 **Автообнаружение** принтеров в локальной сети (Ping Sweep + SNMP probe + Nmap)
- 📊 **SNMP-опрос** v1 / v2c / v3 — статус, картриджи (CMYK), счётчики печати, серийник, прошивка, ошибки
- 🖨 **8 вендоров**: HP, Xerox, **Canon (MF/iR — v1, ADV — v1)**, Brother, Kyocera, Ricoh, Konica Minolta, Epson
- 🔔 **Telegram-уведомления** с настраиваемой периодичностью повтора по типу события (1 раз / 5 мин / 15 мин / 1 ч / 1 день / любое значение)
- 📱 **Web-панель** React 19 + MUI 6 — темная/светлая темы, **3 языка (RU / KK / EN)**
- 📈 **Dashboard** с live-аналитикой: онлайн/оффлайн, ошибки за сутки, картриджи на замену, **6 диаграмм** (Recharts)
- 🛠 **Управление через UI**: ручное добавление принтеров, ручной ввод подсети, кабинет/расположение, **токен Telegram-бота без перезапуска**
- 🔐 **JWT auth + ролевая модель**: Super Admin / Administrator / Operator / Viewer
- 🐳 **Полная контейнеризация** через Docker Compose (9 сервисов)
- 🔄 **WebSocket realtime** обновления
- 🌐 **REST API** с Swagger UI — готов к интеграции с 1С, CRM, Service Desk, Zabbix, Grafana

---

## 🏗 Архитектура

### Сервисы (9 контейнеров)

| Сервис | Технология | Порт |
|---|---|---|
| `postgres` | PostgreSQL 16 Alpine | 5432 |
| `redis` | Redis 7 Alpine (AOF) | 6379 |
| `backend` | FastAPI + uvicorn (Python 3.12) | 8000 |
| `websocket` | FastAPI WebSocket realtime | 8888 |
| `monitoring-service` | asyncio + pysnmp + ping | 9000 |
| `discovery-service` | FastAPI + nmap + SNMP (`network_mode: host`) | 9001 |
| `notification-service` | FastAPI + Telegram Bot API | 9002 |
| `frontend` | React 19 + Vite + MUI 6 → nginx | 8080 |
| `nginx` | Reverse proxy (опционально) | 8081 |

### Потоки данных

```
monitoring (9000) ──ping+SNMP──► принтеры
   │ POST status                              ┐
   │ POST events ───► notification (9002) ────┤ Telegram Bot API
   ▼                                          │
backend (8000) ◄── REST /api/v1/* ── frontend (8080)
   │                                  ▲
   ├─► postgres (5432)                │
   ├─► redis (6379) ── pub/sub ── websocket (8888) ── realtime UI
   ▼
discovery (9001, host net) ── обнаружение ─► backend (новые принтеры)
```

---

## 🚀 Установка за 3 команды

### Требования

- Linux (Ubuntu 22.04+ / Debian 12+ / RHEL 9+) или macOS
- Docker 24+ и Docker Compose v2
- 4 GB RAM (рекомендовано 8 GB), 20 GB диска
- Доступ в подсеть с принтерами (для SNMP)

### Запуск

```bash
git clone https://github.com/rustem2003/ws-printer-monitoring.git
cd ws-printer-monitoring
./install.sh
```

Инсталлер спросит IP сервера, сгенерирует случайные секреты и запустит compose.

### Доступ

| Что | URL |
|---|---|
| 🖥 Web-панель | `http://<SERVER_IP>:8080` |
| 📘 Swagger API | `http://<SERVER_IP>:8000/docs` |

**Дефолтная учётка:** `admin` / `admin123` (смените сразу после входа!)

---

## 🔧 Первичная настройка через UI

1. **Войдите** в систему (`admin` / `admin123`)
2. Откройте **«Telegram бот»** в меню → вставьте токен от `@BotFather` + chat_id → нажмите **«Проверить токен (getMe)»**
3. Откройте **«Принтеры»** → введите подсеть (например `192.168.0.0/24`) → **«Сканировать»**
4. У Canon MF/iR — нажмите ✏ «Изменить» → SNMP версию переключите на `1`
5. Каждому принтеру укажите **Кабинет**
6. Откройте **«Период уведомлений»** — настройте частоту повтора по каждому типу события
7. Смотрите **Dashboard** — данные обновляются автоматически каждые 30 сек

---

## 🌐 Поддержка SNMP версий по вендорам

| Вендор / серия | SNMP версия | Заметка |
|---|---|---|
| **Canon** MF, LBP, iR, iR-ADV | **v1** | Только v1, **не v2c** |
| HP LaserJet, OfficeJet | v2c | |
| Xerox WorkCentre, Phaser, VersaLink | v2c | |
| Brother HL, MFC | v2c | |
| Kyocera ECOSYS | v2c | |
| Ricoh Aficio | v2c | |
| Konica Minolta Bizhub | v2c | |
| Epson WorkForce | v2c | |

Если новый принтер пишет offline при работающем ping — почти всегда нужно
переключить SNMP версию через UI ✏ «Изменить».

---

## 📦 Управление сервисом

```bash
# Статус
docker compose ps

# Логи
docker compose logs -f backend
docker compose logs -f monitoring-service

# Перезапуск / обновление
docker compose restart
docker compose up -d --build

# Резервная копия БД
docker compose exec postgres pg_dump -U printer printerdb | gzip > backup-$(date +%F).sql.gz

# Остановка (данные сохраняются)
docker compose down

# Остановка с удалением volumes (⚠️ удаляет БД)
docker compose down -v
```

---

## 🔌 REST API

Полная документация: `http://<SERVER>:8000/docs` (Swagger UI).

```http
POST   /api/v1/auth/login                          # JWT login
GET    /api/v1/printers                            # List
POST   /api/v1/printers                            # Add manually
PUT    /api/v1/printers/{id}                       # Update
DELETE /api/v1/printers/{id}
POST   /api/v1/printers/{id}/check                 # On-demand SNMP probe
GET    /api/v1/printers/{id}/consumables
GET    /api/v1/events                              # JOIN to printers (name, IP, location)
GET    /api/v1/statistics                          # Overview
GET    /api/v1/statistics/charts                   # Aggregates for dashboard
POST   /api/v1/discovery/start                     # {subnet, method}
GET    /api/v1/telegram-chats                      # CRUD chats
POST   /api/v1/telegram-chats/{id}/test            # Send test message
GET    /api/v1/notification-settings               # Repeat period per event
PUT    /api/v1/notification-settings/{event_type}
GET    /api/v1/system-settings/telegram            # Bot token (masked)
PUT    /api/v1/system-settings/telegram            # Hot-reload without restart
POST   /api/v1/system-settings/telegram/test       # getMe
```

---

## 📁 Структура проекта

```
ws-printer-monitoring/
├── docker-compose.yml          # 9 сервисов
├── .env.example                # Шаблон переменных
├── install.sh                  # Автоинсталлер
├── README.md
├── LICENSE                     # MIT
│
├── backend/                    # FastAPI (Python 3.12)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── migrations/init.sql
│   └── app/
│       ├── main.py
│       ├── core/               # config, database, auth (JWT + bcrypt)
│       ├── models/             # 13 SQLAlchemy моделей
│       ├── routers/            # auth, printers, events, discovery, statistics,
│       │                       # telegram, notification_settings, system_settings
│       └── schemas/            # Pydantic
│
├── monitoring/                 # SNMP/Ping сборщик + on-demand HTTP API
├── discovery/                  # Автообнаружение (Nmap + SNMP probe)
├── notification/               # Telegram-бот (multi-chat, throttle, CMYK + кабинет)
├── frontend/                   # React 19 + Vite + MUI 6 + Recharts
│   ├── public/logo.svg
│   └── src/
│       ├── i18n.tsx            # RU / KK / EN (200+ ключей)
│       ├── api.ts              # axios + JWT interceptor
│       ├── pages/              # Dashboard, Printers, Events, Telegram,
│       │                       # BotSettings, NotificationSettings, Login
│       └── components/         # Shell, Footer
└── nginx/                      # Reverse proxy
```

---

## 🩺 Диагностика проблем

<details>
<summary><b>Принтер пишет offline, но ping проходит</b></summary>

Скорее всего SNMP версия не та. Откройте ✏ «Изменить» принтера →
SNMP версия → **`1`** для Canon MF/iR, `2c` для остальных.
</details>

<details>
<summary><b>Telegram не отправляет сообщения</b></summary>

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"
```
Должно вернуть `{"ok":true,"result":{...}}`. Если `401` — токен невалиден,
получите новый у `@BotFather`.
</details>

<details>
<summary><b>Discovery ничего не находит</b></summary>

Discovery работает в `network_mode: host`. Проверьте:
```bash
docker compose exec discovery-service ping -c 2 192.168.0.1
docker compose exec discovery-service snmpget -v2c -c public 192.168.0.X 1.3.6.1.2.1.1.1.0
```
</details>

<details>
<summary><b>Backend падает с <code>bcrypt password longer than 72 bytes</code></b></summary>

Версия `passlib` несовместима с новым `bcrypt`. В `backend/requirements.txt`
закреплено `bcrypt==3.2.2` — пересоберите образ:
```bash
docker compose up -d --build backend
```
</details>

---

## 🛡 Безопасность

- 🔑 JWT authentication для всех защищённых endpoint
- 🔒 bcrypt-хеширование паролей
- 🚪 Internal token для service-to-service запросов
- 🛡 Маскирование токена Telegram в API (`896***:AAGY***2z1Y`)
- 📋 Audit logs (таблица `audit_logs`)
- 🌐 CORS configurable
- 🔐 Все секреты через `.env` (не в Git)

---

## 🗺 Roadmap

- [ ] WebSocket realtime push событий в UI без polling
- [ ] Экспорт отчётов в Excel и PDF
- [ ] SAML / LDAP / OAuth2 SSO
- [ ] Multi-tenant с изоляцией по организациям
- [ ] Mobile app (React Native / Flutter)
- [ ] Email-уведомления (SMTP)
- [ ] WhatsApp / Slack интеграция
- [ ] Prometheus / Grafana экспортёр метрик

---

## 🤝 Вклад в проект

Pull requests приветствуются. Перед крупными изменениями откройте issue
для обсуждения.

---

## 📞 Поддержка проекта

**Разработчик:** ИП WEB-Soft
**Email:** [info@web-soft.kz](mailto:info@web-soft.kz)

Если проект оказался полезным — поддержите развитие:

💳 **IBAN:** `KZ48722S000035656178`

---

## 📄 Лицензия

[MIT License](LICENSE) © 2026 ИП WEB-Soft

---

<div align="center">

⭐ **Понравился проект? Поставьте звезду на GitHub!** ⭐

</div>
