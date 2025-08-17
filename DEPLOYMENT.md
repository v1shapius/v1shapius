# Инструкции по развертыванию Discord Rating Bot

## 🚀 Быстрый старт

### 1. Предварительные требования

- **Docker** версии 20.10+ и **Docker Compose** версии 2.0+
- **Discord Bot Token** (получить на [Discord Developer Portal](https://discord.com/developers/applications))
- **Git** для клонирования репозитория

### 2. Клонирование и настройка

```bash
# Клонировать репозиторий
git clone <repository-url>
cd discord-rating-bot

# Сделать скрипт развертывания исполняемым
chmod +x deploy.sh

# Создать файл переменных окружения
cp .env.example .env
```

### 3. Настройка переменных окружения

Отредактируйте файл `.env`:

```bash
# Обязательные настройки
DISCORD_TOKEN=your_discord_bot_token_here

# Настройки базы данных (можно оставить по умолчанию для разработки)
POSTGRES_USER=bot_user
POSTGRES_PASSWORD=bot_password

# Настройки Redis (можно оставить по умолчанию для разработки)
REDIS_URL=redis://localhost:6379

# Дополнительные настройки
DEFAULT_LOCALE=ru  # или en для английского
DEFAULT_RESTART_PENALTY=30
VOICE_CHANNEL_DELAY=300
```

### 4. Развертывание

#### Разработка (рекомендуется для начала)

```bash
# Развернуть среду разработки
./deploy.sh dev

# Просмотр логов
./deploy.sh logs

# Остановка сервисов
./deploy.sh stop
```

#### Продакшн

```bash
# Развернуть продакшн среду
./deploy.sh prod

# Просмотр статуса
./deploy.sh status

# Создание резервной копии
./deploy.sh backup
```

## 🔧 Ручная установка (без Docker)

### 1. Установка зависимостей

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt
```

### 2. Настройка базы данных

```bash
# Установить PostgreSQL
# Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib

# macOS:
brew install postgresql

# Windows: скачать с официального сайта

# Создать базу данных
sudo -u postgres psql
CREATE DATABASE discord_bot;
CREATE USER bot_user WITH PASSWORD 'bot_password';
GRANT ALL PRIVILEGES ON DATABASE discord_bot TO bot_user;
\q

# Применить миграции
alembic upgrade head
```

### 3. Настройка Redis

```bash
# Ubuntu/Debian:
sudo apt-get install redis-server

# macOS:
brew install redis

# Windows: скачать с официального сайта

# Запустить Redis
redis-server
```

### 4. Запуск бота

```bash
# Запустить бота
python bot.py
```

## 🐳 Docker развертывание

### Разработка

```bash
# Запустить только базу данных и Redis
docker-compose up -d postgres redis

# Запустить бота
docker-compose up -d bot

# Просмотр логов
docker-compose logs -f bot

# Остановка
docker-compose down
```

### Продакшн

```bash
# Запустить все сервисы
docker-compose -f docker-compose.prod.yml up -d

# Просмотр статуса
docker-compose -f docker-compose.prod.yml ps

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f

# Остановка
docker-compose -f docker-compose.prod.yml down
```

## 📊 Мониторинг

### Логи

```bash
# Логи бота
tail -f logs/bot.log

# Логи Docker
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f postgres
```

### Статус сервисов

```bash
# Проверка состояния
./deploy.sh status

# Проверка здоровья базы данных
docker-compose exec postgres pg_isready -U bot_user -d discord_bot

# Проверка Redis
docker-compose exec redis redis-cli ping
```

### Метрики

```bash
# Prometheus (если включен)
curl http://localhost:9090/metrics

# Grafana (если включен)
# Открыть http://localhost:3000 в браузере
# Логин: admin, пароль: admin (или из переменной GRAFANA_PASSWORD)
```

## 🔒 Безопасность

### Переменные окружения

```bash
# Никогда не коммитьте .env файл
echo ".env" >> .gitignore

# Используйте секреты в продакшне
# Docker Swarm:
echo $DISCORD_TOKEN | docker secret create discord_token -

# Kubernetes:
kubectl create secret generic bot-secrets \
  --from-literal=discord-token=$DISCORD_TOKEN
```

### Сетевая безопасность

```bash
# Ограничить доступ к базе данных
# В docker-compose.prod.yml:
ports:
  - "127.0.0.1:5432:5432"  # Только локальный доступ

# Использовать VPN для удаленного доступа
# Настроить firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 📦 Резервное копирование

### Автоматическое резервное копирование

```bash
# Создать резервную копию
./deploy.sh backup

# Восстановить из резервной копии
./deploy.sh restore backups/discord_bot_backup_20231201_120000.sql
```

### Ручное резервное копирование

```bash
# Резервная копия базы данных
docker-compose exec postgres pg_dump -U bot_user discord_bot > backup.sql

# Резервная копия файлов
tar -czf bot_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  --exclude=venv \
  --exclude=__pycache__ \
  --exclude=*.pyc \
  .
```

## 🔄 Обновления

### Обновление кода

```bash
# Получить последние изменения
git pull origin main

# Пересобрать образы
docker-compose build --no-cache

# Перезапустить сервисы
docker-compose down
docker-compose up -d
```

### Обновление базы данных

```bash
# Создать резервную копию
./deploy.sh backup

# Применить миграции
alembic upgrade head

# Проверить статус
alembic current
```

## 🚨 Устранение неполадок

### Частые проблемы

#### Бот не запускается

```bash
# Проверить логи
./deploy.sh logs

# Проверить переменные окружения
cat .env

# Проверить подключение к базе данных
docker-compose exec postgres psql -U bot_user -d discord_bot -c "SELECT 1;"
```

#### Ошибки базы данных

```bash
# Проверить статус PostgreSQL
docker-compose exec postgres pg_isready

# Перезапустить базу данных
docker-compose restart postgres

# Проверить логи
docker-compose logs postgres
```

#### Проблемы с Redis

```bash
# Проверить статус Redis
docker-compose exec redis redis-cli ping

# Перезапустить Redis
docker-compose restart redis

# Очистить кэш
docker-compose exec redis redis-cli FLUSHALL
```

### Логи и отладка

```bash
# Включить подробное логирование
export LOG_LEVEL=DEBUG

# Просмотр системных ресурсов
docker stats

# Проверка дискового пространства
df -h
docker system df
```

## 📋 Чек-лист развертывания

- [ ] Установлен Docker и Docker Compose
- [ ] Создан Discord Bot и получен токен
- [ ] Настроен файл .env
- [ ] Запущены сервисы базы данных и Redis
- [ ] Бот успешно подключился к Discord
- [ ] Созданы необходимые таблицы в базе данных
- [ ] Настроены права доступа для бота на сервере
- [ ] Протестированы основные команды
- [ ] Настроено резервное копирование
- [ ] Настроен мониторинг (опционально)

## 🆘 Получение помощи

### Полезные команды

```bash
# Справка по скрипту развертывания
./deploy.sh help

# Статус всех сервисов
./deploy.sh status

# Просмотр логов в реальном времени
./deploy.sh logs

# Создание резервной копии
./deploy.sh backup
```

### Документация

- [Discord.py документация](https://discordpy.readthedocs.io/)
- [SQLAlchemy документация](https://docs.sqlalchemy.org/)
- [Docker документация](https://docs.docker.com/)
- [Alembic документация](https://alembic.sqlalchemy.org/)

### Поддержка

- Создать Issue в GitHub репозитории
- Проверить логи для диагностики проблем
- Убедиться, что все переменные окружения настроены правильно