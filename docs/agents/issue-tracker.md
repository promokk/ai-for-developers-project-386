# Issue tracker: GitHub

Задачи и спецификации этого репозитория хранятся в GitHub Issues. Для всех операций используется `gh` CLI.

## Соглашения

- **Создать задачу**: `gh issue create --title "..." --body "..."`. Для многострочного описания используйте heredoc.
- **Прочитать задачу**: `gh issue view <number> --json number,title,body,labels,comments`.
- **Получить список задач**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` с подходящими фильтрами `--label` и `--state`.
- **Сделать задачу подзадачей**: `gh issue create --parent <parent> ...` или затем `gh issue edit <parent> --add-sub-issue <child>` (`gh` 2.94+). В старых версиях: `gh api --method POST repos/<owner>/<repo>/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>` (database id, как в **Блокировках** ниже). Если подзадачи недоступны, добавьте `Part of #<parent>` в начало описания дочерней задачи.
- **Блокировки**: используйте встроенные зависимости GitHub Issues — каноническое представление, видимое в UI. Добавьте связь через `gh issue create --blocked-by <n>,<n> ...` или `gh issue edit <child> --add-blocked-by <blocker>` (`gh` 2.94+). В старых версиях: `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, где `<blocker-db-id>` — числовой **database id** блокера (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, не `#number` и не `node_id`). Если зависимости недоступны, добавьте `Blocked by: #<n>, #<n>` в начало описания дочерней задачи. Задача разблокирована, когда все блокеры закрыты.
- **Посчитать открытые блокеры**: `gh api repos/<owner>/<repo>/issues/<n> --jq .issue_dependencies_summary.blocked_by` (только открытые; 0 означает, что можно начинать). `gh issue view <n> --json blockedBy` также возвращает закрытые блокеры, поэтому фильтруйте их: `--jq '[.blockedBy.nodes[] | select(.state == "OPEN")] | length'`.
- **Комментировать**: `gh issue comment <number> --body "..."`.
- **Добавить / удалить метки**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`.
- **Закрыть**: сначала `gh issue comment <number> --body "..."` с объяснением, затем `gh issue close <number>`. Для уже закрытой задачи `gh issue close --comment` удаляет комментарий, но завершается с кодом 0.

Репозиторий определяется из `git remote -v`; внутри клона `gh` делает это автоматически.

Создавайте задачи только в репозитории пользователя. Никогда не создавайте их в `mattpocock/skills` (репозитории, из которого взяты навыки), если он не принадлежит пользователю. В форке `gh` может выбрать upstream-репозиторий, поэтому перед первым `gh issue create` в сессии проверьте назначение через `gh repo view --json nameWithOwner` и подтвердите его у пользователя, если это не его репозиторий.

## Pull request как источник запросов для triage

**PR как источник запросов: нет.** _(Установите `yes`, если внешние PR в этом репозитории считаются запросами на функциональность; `/triage` читает этот флаг.)_

При `yes` PR проходят через те же метки и состояния, что и задачи, с использованием аналогов `gh pr`:

- **Прочитать PR**: `gh pr view <number>`, затем `gh pr view <number> --comments` (вне TTY `--comments` выводит только комментарии, без описания) и `gh pr diff <number>` для diff.
- **Получить внешние PR для triage**: `gh api --paginate 'repos/{owner}/{repo}/pulls?state=open' --jq '.[] | select(.author_association | IN("OWNER","MEMBER","COLLABORATOR") | not) | {number, title, author: .user.login, author_association, labels: [.labels[].name]}'`.
- **Комментировать / менять метки / закрывать**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub использует общее пространство номеров для задач и PR, поэтому `#42` может обозначать любой из них: проверьте `gh pr view 42`, затем при необходимости `gh issue view 42`.

## Когда навык требует опубликовать в issue tracker

Создайте GitHub issue.

## Когда навык требует получить соответствующий тикет

Прочитайте его, как описано в **Прочитать задачу** выше.

## Операции wayfinding

Используются `/wayfinder`. **Карта** — одна задача, **дочерние задачи** — тикеты.

- **Карта**: одна задача с меткой `wayfinder:map`, содержащая Notes / Decisions-so-far / Fog. `gh issue create --label wayfinder:map`.
- **Дочерний тикет**: задача, связанная с картой как GitHub sub-issue (см. **Сделать задачу подзадачей**). Если sub-issues недоступны, добавьте дочернюю задачу в список задач карты и `Part of #<map>` в начало её описания. Метки: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). После назначения тикет закрепляется за ведущим разработчиком.
- **Блокировки**: см. **Блокировки** в разделе «Соглашения».
- **Запрос frontier**: получите открытые дочерние задачи карты (`gh issue list --state open` в области sub-issues / списка задач карты), исключите задачи с открытым блокером (см. **Посчитать открытые блокеры** или строку `Blocked by`) либо исполнителем; первая в порядке карты имеет приоритет.
- **Назначение**: `gh issue edit <n> --add-assignee @me`, первая запись в сессии.
- **Завершение**: `gh issue comment <n> --body "<answer>"`, затем `gh issue close <n>`, затем добавьте указатель контекста (gist + ссылка) в Decisions-so-far карты.
