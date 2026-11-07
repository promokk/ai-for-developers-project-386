# AGENTS.md

Правила для ИИ-агентов и разработчиков проекта «Календарь звонков».

## Окружение

Всё окружение разработки управляется через mise (`mise.toml`): версии
инструментов, переменные окружения, задачи, хуки и daemons. Ничего не
устанавливай в обход mise.

- `mise install && mise run setup` — установка окружения с нуля.
- `mise run check` — все проверки проекта. **Команда обязана быть зелёной до
  завершения любой задачи** — та же команда гоняется в GitHub Actions на
  каждый push.
- `mise run fix` — безопасные автофиксы линтеров и форматтеров.
- `mise run test` — тесты бэкенда (pytest).
- `mise daemons start|stop|status` — фоновые dev-серверы (backend :8000,
  frontend :5173) через pitchfork.

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

## Контракт API

- Источник правды — `contracts/main.tsp` (TypeSpec). Сначала меняется спека,
  потом реализация.
- `contracts/openapi/openapi.yaml` и `frontend/src/api/` — **генерируемые
  файлы**, вручную не редактируются. Обновление: `mise run gen`.
- FastAPI реализует эндпоинты по спеке; контрактный тест
  (`backend/tests/test_contract.py`) сверяет приложение со спекой.

## Проверки качества

Набор инструментов выбран по
[dev-quality-gates](https://github.com/mokevnin/dev-quality-gates):

- Python: Ruff (линт + формат), ty (типы), deptry (зависимости), pytest.
- TS/React: Oxlint + oxfmt (с `--deny-warnings`), `tsc --noEmit` (strict).
- API: vacuum (линт OpenAPI), oasdiff (breaking changes против base-ветки).
- Прочее: jactionlint (workflow), Betterleaks (секреты), rumdl (Markdown),
  typos (опечатки), commitlint (Conventional Commits).
- Git-хуки — hk (`hk.pkl`): pre-commit (быстрые проверки staged-файлов),
  pre-push (`mise run check`), commit-msg (commitlint).

Правила:

- Линт-правила не отключаются, чтобы прогнать изменение. Исключение — один
  путь и одно правило, с причиной в комментарии; такое решение принимает
  человек.
- `.github/workflows/hexlet-check.yml` не изменять и не удалять — его
  использует проверка Хекслета.
