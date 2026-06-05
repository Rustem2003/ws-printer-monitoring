#!/usr/bin/env bash
# WS Printer Monitoring — quick installer
# Использование: ./install.sh [SERVER_IP]
set -euo pipefail

SERVER_IP="${1:-}"

echo "=== WS Printer Monitoring installer ==="

# Check docker
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Docker не установлен. Установите: curl -fsSL https://get.docker.com | sudo sh"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "❌ Docker Compose v2 не установлен."
  exit 1
fi

# Ask for IP if not provided
if [[ -z "$SERVER_IP" ]]; then
  DEFAULT_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
  read -r -p "IP адрес сервера для доступа из браузера [$DEFAULT_IP]: " SERVER_IP
  SERVER_IP="${SERVER_IP:-$DEFAULT_IP}"
fi
echo "✓ Сервер: $SERVER_IP"

# Generate .env
if [[ -f .env ]]; then
  echo "⚠️  .env уже существует — пропуск генерации"
else
  cp .env.example .env
  if command -v openssl >/dev/null 2>&1; then
    PG_PASS=$(openssl rand -hex 16)
    SECRET=$(openssl rand -hex 32)
    INTERNAL=$(openssl rand -hex 24)
    # macOS sed needs '', Linux sed doesn't
    if [[ "$(uname)" == "Darwin" ]]; then SED_I=(-i ''); else SED_I=(-i); fi
    sed "${SED_I[@]}" \
      -e "s|CHANGE_ME_RANDOM_PASSWORD|$PG_PASS|" \
      -e "s|CHANGE_ME_64_CHAR_HEX_STRING|$SECRET|" \
      -e "s|CHANGE_ME_INTERNAL_TOKEN|$INTERNAL|" \
      -e "s|CHANGE_ME_SERVER_IP|$SERVER_IP|g" \
      .env
    echo "✓ .env создан со случайными секретами"
  else
    echo "❌ openssl не найден — отредактируйте .env вручную"
    exit 1
  fi
fi

# Validate compose
echo "✓ Проверка docker-compose.yml..."
docker compose config --quiet

# Build & up
echo "✓ Запуск (build занимает 5-10 минут при первом старте)..."
docker compose up -d --build

# Wait health
echo "✓ Ждём готовности БД..."
for i in {1..30}; do
  if docker compose exec -T postgres pg_isready -U printer >/dev/null 2>&1; then break; fi
  sleep 2
done

echo ""
echo "========================================"
echo "🎉 Готово!"
echo ""
echo "  Web-панель:  http://$SERVER_IP:8080"
echo "  Swagger:     http://$SERVER_IP:8000/docs"
echo ""
echo "  Логин:       admin"
echo "  Пароль:      admin123"
echo ""
echo "  ⚠️  Не забудьте сменить пароль и настроить Telegram-бот в UI!"
echo "========================================"
