# Discord Rating Bot - Структура проекта

## Основные компоненты

### 1. Основные модули (cogs)
- `match_management.py` - Управление матчами и их жизненным циклом
- `rating_system.py` - Рейтинговая система Глико-2
- `voice_control.py` - Контроль голосовых каналов и трансляций
- `admin.py` - Административные функции
- `draft_verification.py` - Проверка и подтверждение драфтов

### 2. Сервисы
- `match_service.py` - Бизнес-логика матчей
- `rating_service.py` - Расчеты рейтинга
- `voice_service.py` - Работа с голосовыми каналами
- `notification_service.py` - Система уведомлений

### 3. Модели данных
- `models/` - SQLAlchemy модели
- `schemas/` - Pydantic схемы для валидации

### 4. Утилиты
- `utils/` - Вспомогательные функции
- `locales/` - Файлы локализации
- `config/` - Конфигурация

### 5. Docker и развертывание
- `docker-compose.yml` - Основной файл развертывания
- `Dockerfile` - Образ бота
- `.env.example` - Пример переменных окружения