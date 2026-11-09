import { useEffect, useState } from "react";

import { apiListEventTypes } from "./api";
import type { EventType } from "./api";

export default function EventTypesPage() {
  const [eventTypes, setEventTypes] = useState<EventType[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const created = new URLSearchParams(window.location.search).get("created") === "1";

  useEffect(() => {
    let active = true;

    void apiListEventTypes({ baseUrl: "" }).then(({ data }) => {
      if (!active) {
        return;
      }
      if (data) {
        setEventTypes(data);
      } else {
        setFailed(true);
      }
    });

    return () => {
      active = false;
    };
  }, [attempt]);

  return (
    <main className="container event-types-page">
      <h1>Типы событий</h1>
      {created && <p role="status">Тип события создан</p>}
      {failed ? (
        <div>
          <p role="alert">Не удалось загрузить типы событий</p>
          <button
            onClick={() => {
              setFailed(false);
              setAttempt((value) => value + 1);
            }}
            type="button"
          >
            Повторить
          </button>
        </div>
      ) : eventTypes === null ? (
        <p role="status">Загрузка типов событий…</p>
      ) : eventTypes.length === 0 ? (
        <div>
          <p>Типов событий пока нет</p>
          <p>Создайте первый тип, чтобы гости могли выбрать подходящий звонок.</p>
          <a href="/event-types/new">Создать тип события</a>
        </div>
      ) : (
        <>
          <a href="/event-types/new">Создать тип события</a>
          <ul aria-label="Доступные типы событий" className="event-types-list">
            {eventTypes.map((eventType) => (
              <li key={eventType.id}>
                <h2>{eventType.name}</h2>
                <p>{eventType.description}</p>
                <p>{eventType.durationMinutes} минут</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </main>
  );
}
