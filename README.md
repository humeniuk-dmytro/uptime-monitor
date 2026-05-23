# URL Uptime Monitor

Мінімалістичний backend-сервіс для моніторингу доступності HTTP-ендпоінтів.

## Стек

- **Python 3.12+** / FastAPI / SQLAlchemy (async)
- **MariaDB** — основне сховище
- **httpx** — HTTP-клієнт для пінгів
- **asyncio** — фоновий scheduler (без зовнішніх черг)

---

## Як запустити

### Через Docker (рекомендовано)

```bash
docker-compose up --build
```

API буде доступне на `http://localhost:8000`
Swagger UI: `http://localhost:8000/docs`

### Локально (без Docker)

1. Підняти MariaDB будь-яким способом
2. Створити `.env` файл:

```bash
cp .env.example .env
# відредагувати DATABASE_URL під свій хост
```

3. Встановити залежності та запустити:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Ендпоінти

| Метод | URL | Опис |
|---|---|---|
| POST | `/monitors` | Створити монітор |
| GET | `/monitors` | Список моніторів |
| GET | `/monitors/{id}` | Деталі монітора |
| PATCH | `/monitors/{id}` | Оновити монітор |
| DELETE | `/monitors/{id}` | М'яке видалення |
| GET | `/monitors/{id}/history` | Історія перевірок |
| GET | `/monitors/{id}/uptime` | Uptime % за вікном |
| GET | `/healthz` | Healthcheck |

### Приклад створення монітора

```bash
curl -X POST http://localhost:8000/monitors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Google",
    "url": "https://google.com",
    "check_interval_sec": 60,
    "expected_status": 200,
    "timeout_sec": 10
  }'
```

### Uptime за останні 24 години

```bash
curl http://localhost:8000/monitors/1/uptime?window=24h
```

Доступні вікна: `1h`, `24h`, `7d`, `30d`

---

## Схема БД

### Таблиці

- **monitors** — список сервісів що моніторяться
- **checks** — кожен результат HTTP-пінгу
- **transitions** — лог змін стану (unknown/up/down)

### Індекси та їх обґрунтування

| Індекс | Таблиця | Причина |
|---|---|---|
| `idx_monitors_status_last_checked` | monitors | Воркер шукає активні монітори по `status + last_checked_at` на кожен тік |
| `idx_checks_monitor_checked` | checks | `/history` і `/uptime` завжди фільтрують по `monitor_id + checked_at DESC` |
| `idx_transitions_monitor` | transitions | Лог переходів по конкретному монітору |

---

## State machine
unknown ──(1й успіх)──► up
unknown ──(3 фейли)──► down
up      ──(3 фейли підряд)──► down
down    ──(1 успіх)──► up

При кожному переході пишеться рядок в таблицю `transitions`.
Якщо заданий `webhook_url` — відправляється POST-запит.

---

## Тести

```bash
pytest tests/ -v
```

---

## На що пішов час

| Фаза | Час |
|---|---|
| Схема БД + моделі | ~45 хв |
| REST API (CRUD + history + uptime) | ~1.5 год |
| Worker + state machine + webhook | ~1.5 год |
| Docker + конфігурація | ~30 хв |
| Тести | ~45 хв |
| README + документація | ~20 хв |

---

## Що б доробив у v2

1. **Аутентифікація** — API keys або JWT, зараз API повністю відкрите
2. **Pagination** на `/history` — курсорна пагінація замість простого `limit`
3. **Prometheus `/metrics`** — лічильники `checks_total`, `failures_total`
4. **Maintenance windows** — не алертити в заданий часовий проміжок
5. **Rate-limit на webhook** — не більше 1 сповіщення / 5 хвилин на монітор
6. **Діапазони статусів** — `expected_status: "2xx"` або `[200, 201, 204]`
7. **Окремий worker-процес** — `python -m worker` замість asyncio task для кращої ізоляції
8. **Alerting** — email/Slack нотифікації крім webhook
