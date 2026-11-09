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

Коммиты — по Conventional Commits (`feat:`, `fix:`, …), проверяются
commitlint. Правила для агентов — в [AGENTS.md](AGENTS.md).

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
