# Календарь звонков

[![hexlet-check](https://github.com/promokk/ai-for-developers-project-386/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/promokk/ai-for-developers-project-386/actions)
[![check](https://github.com/promokk/ai-for-developers-project-386/actions/workflows/check.yml/badge.svg)](https://github.com/promokk/ai-for-developers-project-386/actions)

Разработайте совместно с ИИ сервис для бронирования календаря

Учебный проект Хекслета: <https://ru.hexlet.io/programs/ai-for-developers>
Как это должно работать: <https://files.hexlet.app/a/2ipc5m>

## Стек

- Бэкенд: Python 3, FastAPI, uv, pytest.
- Фронтенд: React, TypeScript, Vite.
- Контракт API: TypeSpec → OpenAPI → клиентский SDK (@hey-api/openapi-ts).
- Окружение: mise (версии, задачи, хуки, daemons), hk (git-хуки).
- Проверки: Ruff, ty, deptry, Oxlint, oxfmt, vacuum, oasdiff, jactionlint,
  Betterleaks, OSV-Scanner, rumdl, typos, commitlint
  ([подборка](https://github.com/mokevnin/dev-quality-gates)).

## Установка

```bash
git clone https://github.com/promokk/ai-for-developers-project-386.git
cd ai-for-developers-project-386
mise install   # ставит инструменты и запускает setup (postinstall-хук)
```

Если хук не сработал: `mise run setup` — ставит зависимости (uv, pnpm),
генерирует OpenAPI и SDK, устанавливает git-хуки.

## Использование

```bash
mise daemons start    # backend :8000 и frontend :5173 в фоне
mise daemons status   # состояние серверов
mise daemons stop     # остановить
```

Фронтенд: <http://127.0.0.1:5173> (проксирует `/api` на бэкенд).

Команды:

```bash
mise run check   # все проверки (линтеры, типы, тесты, контракт) — как в CI
mise run test    # pytest
mise run fix     # автофиксы
mise run gen     # TypeSpec -> OpenAPI -> клиентский SDK
mise run build   # сборка фронтенда
```

Сквозные сценарии против уже запущенного приложения, без локальных dev-серверов:

```bash
CALENDAR_BASE_URL=https://example.com mise run test:external
```

## Production-контейнер

```bash
docker build -t call-calendar .
docker run --rm -p 8080:8080 -e PORT=8080 call-calendar
```

Приложение откроется на <http://127.0.0.1:8080>. Без `PORT` контейнер
использует порт 8000. FastAPI отдаёт API и собранный SPA, включая прямые
переходы по клиентским URL. Проверить запущенный контейнер можно командой
`CALENDAR_BASE_URL=http://127.0.0.1:8080 mise run test:external`.

Коммиты — по Conventional Commits (`feat:`, `fix:`, …), проверяются
commitlint. Правила для агентов — в [AGENTS.md](AGENTS.md).

## Railway MCP в Kimi Code

Проектная конфигурация `.kimi-code/mcp.json` подключает удалённый Railway MCP
напрямую по HTTP с OAuth. Railway CLI и переменные с учётными данными для этого
не нужны.

1. После добавления конфигурации начните новую сессию Kimi Code в корне проекта:
   уже открытая сессия не подключает новые проектные серверы.
2. Проверьте URL сервера в запросе доверия и разрешите доверенный workspace.
3. Выполните `/mcp-config login railway` и завершите OAuth-вход в браузере.
4. Выполните `/mcp` и проверьте, что сервер `railway` подключён и его инструменты
   доступны.

## Ограничения публичного демо

**[Открыть календарь звонков](https://web-production-25162988.up.railway.app)**

Публичное приложение — учебное демо, а не production-сервис.

Созданные типы событий, брони и ключи идемпотентности хранятся только в памяти.
Перезапуск или повторный деплой удаляет их, а стартовые типы событий создаются
заново с новыми идентификаторами. Поддерживается только один процесс и одна
реплика приложения.

Авторизации нет: любой, у кого есть адрес приложения, может просматривать и
изменять данные. Имена и адреса электронной почты гостей публично доступны.
Не используйте реальные персональные данные.

## Релизы

Релизы автоматизированы через release-please. После появления подходящего
Conventional Commit (`feat:`, `fix:` и др.) в `main` workflow
`.github/workflows/release-please.yml` создаёт или обновляет release PR.

Для публикации релиза проверьте и влейте release PR. После этого workflow
создаст GitHub Release и тег. Номер версии и changelog обновляются в release PR;
создавать релиз вручную для проверки процесса не нужно.

---

<details>
<summary>Автоматические тесты Хекслета</summary>

Тесты запускаются на каждый коммит. За запуск отвечает файл `.github/workflows/hexlet-check.yml` — не удаляйте и не переименовывайте ни его, ни репозиторий.

</details>

## О Хекслете

[Хекслет](https://ru.hexlet.io/) — школа программирования: авторские программы обучения с практикой, поддержкой наставников и реальными проектами, которые остаются в резюме. Этот репозиторий — один из таких проектов.
