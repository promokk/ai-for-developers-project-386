# AGENTS.md

Правила для ИИ-агентов и разработчиков проекта «Календарь звонков».

## Обзор проекта

Учебный проект Хекслета (программа «ИИ для разработчиков»): сервис
бронирования слотов календаря для звонков. Монорепозиторий из трёх частей:

- `backend/` — API на FastAPI (пакет `calendar_api`, исходники в
  `backend/src/calendar_api/`). Состояние (список бронирований) хранится
  в памяти процесса, базы данных нет. Зависимости: fastapi, pydantic,
  uvicorn; dev — pytest, httpx2 (клиент для TestClient), pyyaml, deptry.
- `frontend/` — SPA на React 19 + TypeScript + Vite. Исходники в
  `frontend/src/`; точка входа `main.tsx`, корневой компонент `App.tsx`.
  Vite проксирует `/api` на бэкенд `http://127.0.0.1:8000`.
- `contracts/` — контракт API на TypeSpec (`main.tsp`). Из него
  генерируются `contracts/openapi/openapi.yaml` и клиентский TS SDK
  (`@hey-api/openapi-ts`) в `frontend/src/api/`.

Эндпоинты (префикс `/api`): `GET /api/health`, `GET /api/event-types`,
`POST /api/event-types` (201),
`GET /api/event-types/{eventTypeId}/availability`,
`GET /api/bookings?scope=upcoming`, `POST /api/bookings` (201). Модель
`EventType`: `id`, `name`, `description`, `durationMinutes`. Модель `Booking`:
`id`, `guestName`, `guestEmail`, `startsAt`, `endsAt`, вложенный `eventType`
(camelCase в JSON; в Python — snake_case через
`pydantic.alias_generators.to_camel`).

Корневой `Dockerfile` собирает единый production-образ: FastAPI обслуживает
API и собранный SPA из `/app/static`, включая fallback для клиентских URL.
Контейнер запускает один Uvicorn worker на `0.0.0.0` и порте `PORT`
(по умолчанию 8000) от non-root пользователя.

## Окружение

Всё окружение разработки управляется через mise (`mise.toml`): версии
инструментов, переменные окружения, задачи, хуки и daemons. Ничего не
устанавливай в обход mise. JS-зависимости — pnpm workspace (пакеты:
`contracts`, `frontend`), Python — uv (`backend/.venv`).

- `mise install && mise run setup` — установка окружения с нуля
  (зависимости, Chromium для Playwright, генерация OpenAPI/SDK, git-хуки hk).
- `mise run check` — все проверки проекта. **Команда обязана быть зелёной до
  завершения любой задачи** — та же команда гоняется в GitHub Actions на
  каждый push (`.github/workflows/check.yml`).
- `mise run fix` — безопасные автофиксы линтеров и форматтеров.
- `mise run test` — тесты бэкенда (pytest).
- `mise run test:frontend` — браузерные тесты фронтенда (Playwright).
- `CALENDAR_BASE_URL=<URL> mise run test:external` — внешние HTTP- и
  браузерные сценарии против уже запущенного приложения, без dev-серверов.
- `mise run build` — сборка фронтенда (vite build).
- `mise daemons start|stop|status` — фоновые dev-серверы (backend :8000,
  frontend :5173) через pitchfork. Альтернатива на переднем плане:
  `mise run dev:backend` / `mise run dev:frontend`.

## Conventional Commits

Все коммиты — строго по Conventional Commits:

```text
<тип>(<область>): <описание в повелительном наклонении>
```

- Типы: `feat`, `fix`, `chore`, `docs`, `ci`, `build`, `refactor`, `test`,
  `perf`, `style`, `revert`.
- Примеры: `feat(backend): добавить эндпоинт отмены бронирования`,
  `fix(frontend): починить статус API на главной`, `chore: обновить ruff`.
- Сообщение проверяется commitlint в commit-msg хуке hk и в CI — нестандартный
  коммит не пройдёт.

После завершения задачи или подзадачи добавь `Closes #<номер>` в тело коммита,
оставь в GitHub Issue комментарий с результатом и ссылкой на коммит и закрой её
через `gh issue close <номер>`.

## Контракт API

- Источник правды — `contracts/main.tsp` (TypeSpec). Сначала меняется спека,
  потом реализация.
- `contracts/openapi/openapi.yaml` и `frontend/src/api/` — **генерируемые
  файлы**, вручную не редактируются. Обновление: `mise run gen`.
  Задача `check:generated` падает, если сгенерированные файлы не свежие.
- FastAPI реализует эндпоинты по спеке; контрактный тест
  (`backend/tests/test_contract.py`) сверяет, что все пути и методы из
  `openapi.yaml` присутствуют в приложении.
- В CI дополнительно `oasdiff breaking` ловит ломающие изменения спеки
  относительно base-ветки.

## Тестирование

- Backend: pytest в `backend/tests/` (`mise run test`). HTTP-запросы гоняются
  через `fastapi.testclient.TestClient`.
- `test_contract.py` — контрактный тест (приложение ↔ OpenAPI-спека);
  обязан проходить при любом изменении API.
- Frontend: браузерные E2E-тесты Playwright в `frontend/tests/`
  (`mise run test:frontend`), Chromium с desktop viewport. Дополнительно
  качество обеспечивается линтерами и `tsc --noEmit` (strict).

## Проверки качества

Набор инструментов выбран по
[dev-quality-gates](https://github.com/mokevnin/dev-quality-gates):

- Python: Ruff (линт + формат, правила `B, C901, E, F, I, RUF, S, SIM, UP`;
  в тестах разрешён `S101`), ty (типы), deptry (зависимости), pytest.
- TS/React: Oxlint + oxfmt (с `--deny-warnings`), `tsc --noEmit` (strict),
  Playwright. Генерируемый `frontend/src/api/**` исключён из линта
  в pre-commit хуке.
- API: vacuum (линт OpenAPI), oasdiff (breaking changes против base-ветки).
- Прочее: jactionlint (workflow), Betterleaks (секреты), rumdl (Markdown),
  typos (опечатки), commitlint (Conventional Commits).
- Git-хуки — hk (`hk.pkl`): pre-commit (быстрые проверки staged-файлов),
  pre-push (`mise run check`), commit-msg (commitlint). В hk stash отключён
  намеренно: на Windows stash untracked-файлов периодически теряет файлы.

Правила:

- Линт-правила не отключаются, чтобы прогнать изменение. Исключение — один
  путь и одно правило, с причиной в комментарии; такое решение принимает
  человек.
- `.github/workflows/hexlet-check.yml` не изменять и не удалять — его
  использует проверка Хекслета.

## Стиль кода

- Документация, комментарии и сообщения коммитов — на русском; код и
  идентификаторы — на английском.
- Python: snake_case, строгая типизация (проверяется ty); JSON-поля в
  camelCase через pydantic-алиасы (`to_camel`, `populate_by_name=True`).
- TypeScript: strict-режим, `verbatimModuleSyntax` (типы импортируются через
  `import type`), форматирование — oxfmt.
- Комментарии пишутся только там, где неочевидно «почему», а не «что».

## Безопасность

- Секреты в репозитории запрещены: Betterleaks проверяет дерево в pre-commit
  и в `mise run check` (конфиг `.betterleaks.toml`).
- Workflow GitHub Actions закреплены по полному SHA. По умолчанию используется
  `permissions: {}`; необходимые права выдаются на уровне job. Для
  release-please разрешены только `contents: write` и `pull-requests: write`.
- Dev-серверы слушают только `127.0.0.1`.

## Agent skills

### Issue tracker

Задачи и спецификации хранятся в GitHub Issues этого репозитория. См. `docs/agents/issue-tracker.md`.

### Triage labels

Используются пять стандартных меток triage с одноимёнными строками. См. `docs/agents/triage-labels.md`.

### Domain docs

Используется single-context: один `GLOSSARY.md` и общий `docs/adr/` в корне. См. `docs/agents/domain.md`.
