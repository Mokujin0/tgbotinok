# 🌐 Domain Watcher Bot

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Многофункциональный Telegram-бот для мониторинга доступности доменов, подбора похожих имен и отслеживания момента освобождения доменов. Написан на чистом `requests` без использования тяжелых фреймворков.

---

## 🚀 Основные возможности

- **🔍 Проверка:** Мгновенный чекинг через локальный WHOIS и Namecheap API.
- **💡 Поиск:** Генерация и поиск похожих свободных доменных имен по ключевым словам.
- **👁️ Отслеживание:** Автоматические уведомления, когда интересующий вас домен станет свободным.
- **📍 Геолокация:** Преобразование координат в человекочитаемый адрес.
- **📅 Автоматизация:** Ежедневные отчеты администратору и утренние приветствия пользователям.
- **📊 Статистика:** Логирование сообщений и учет активности пользователей.

---

## 🛠 Технический стек

- **Core:** Python 3.10+
- **API Interaction:** `requests`
- **WHOIS:** `python-whois` (требуется системная утилита `whois`)
- **Scheduling:** `APScheduler`
- **Data Storage:** CSV (пользователи), JSON (конфиги/watchlist), LOG (история сообщений)

---

## 📦 Установка и запуск

### 1. Подготовка системы
Для работы библиотеки `python-whois` в Linux необходимо установить системную утилиту `whois`:

**Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install whois -y
```

**Arch Linux:**
```bash
sudo pacman -S whois
```

### 2. Клонирование и настройка

```bash
# Переход в папку проекта
cd /home/user/tgbotinok

# Создание и активация виртуального окружения
python -m venv .venv
source .venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка окружения
cp .env.example .env
```

## Структура

- `run.py` — запуск
- `config.json` — настройки бота
- `tasks.json` — расписание (8:00 и 23:55 по Москве)
- `data/` — users.csv, watchlist.json, логи, отчёты
- `utils/` — модули

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/me` | Ваш chat_id и username |
| `/check domain.com` | Проверка WHOIS + Namecheap |
| `/search keyword` | Поиск свободных похожих доменов |
| `/watch domain.com` | Уведомление при освобождении |
| `/unwatch domain.com` | Убрать из отслеживания |

## API

- **RDAP** (rdap.org) — бесплатно, без ключа, без депозита. Используется по умолчанию.
- WHOIS: python-whois library (системная утилита `whois`)
- WhoisXML Domain Availability API (опционально, для большей точности)
- Namecheap API (опционально)

Источники доступности опрашиваются по очереди: сначала бесплатный **RDAP**, затем WhoisXML, Namecheap и локальный WHOIS. Опрос прекращается на первом однозначном ответе.

`WHOIS_API_KEY` (WhoisXML) и ключи Namecheap **необязательны** — без них бот работает на RDAP + локальном WHOIS бесплатно. Namecheap Sandbox нужен только для проверки интеграции: он не отражает реальные регистрации и не должен быть источником истины для `/search` и отслеживания.
