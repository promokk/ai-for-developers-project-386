import { useEffect, useState } from "react";

import { apiListBookings } from "./api";
import type { Booking } from "./api";

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  weekday: "long",
  day: "numeric",
  month: "long",
  timeZone: "Europe/Moscow",
});
const timeFormatter = new Intl.DateTimeFormat("ru-RU", {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/Moscow",
});

export default function UpcomingEventsPage() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    let active = true;

    void apiListBookings({ baseUrl: "", query: { scope: "upcoming" } }).then(({ data }) => {
      if (!active) {
        return;
      }
      if (data) {
        setBookings(data);
      } else {
        setFailed(true);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const upcomingBookings = (bookings ?? []).filter(
    (booking) => new Date(booking.endsAt).getTime() > now.getTime(),
  );
  const groups = new Map<string, Booking[]>();
  for (const booking of upcomingBookings) {
    const date = dateFormatter.format(new Date(booking.startsAt));
    groups.set(date, [...(groups.get(date) ?? []), booking]);
  }

  return (
    <main className="container events-page">
      <div className="events-heading">
        <h1>Предстоящие события</h1>
        <p>Запланированные бронирования · Europe/Moscow</p>
      </div>
      {failed ? (
        <p role="alert">Не удалось загрузить предстоящие события</p>
      ) : bookings === null ? (
        <p role="status">Загрузка предстоящих событий…</p>
      ) : upcomingBookings.length === 0 ? (
        <section className="events-empty">
          <h2>Предстоящих событий нет</h2>
          <p>Новые бронирования появятся здесь автоматически</p>
        </section>
      ) : (
        <div className="agenda-days">
          {[...groups.entries()].map(([date, dayBookings]) => (
            <section aria-label={date} className="agenda-day" key={date}>
              <h2>{date}</h2>
              <div className="agenda-list">
                {dayBookings.map((booking) => {
                  const startsAt = new Date(booking.startsAt);
                  const endsAt = new Date(booking.endsAt);
                  const isCurrent = startsAt <= now && endsAt > now;
                  return (
                    <article className="agenda-item" key={booking.id}>
                      <div className="agenda-time">
                        <strong>{timeFormatter.format(startsAt)}</strong>
                        <span>{timeFormatter.format(endsAt)}</span>
                      </div>
                      <div className="agenda-type">
                        <strong>{booking.eventType.name}</strong>
                        <span>{booking.eventType.durationMinutes} минут</span>
                      </div>
                      <div className="agenda-guest">
                        <strong>{booking.guestName}</strong>
                        <a href={`mailto:${booking.guestEmail}`}>{booking.guestEmail}</a>
                      </div>
                      {isCurrent ? <span className="events-status">Идёт сейчас</span> : null}
                    </article>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
