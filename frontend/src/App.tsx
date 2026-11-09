import BookingPage from "./BookingPage";
import EventTypeCreatePage from "./EventTypeCreatePage";
import EventTypesPage from "./EventTypesPage";
import UpcomingEventsPage from "./UpcomingEventsPage";

const features = [
  "Бронирование слотов с 09:00 до 18:00.",
  "Проверка конфликта при бронировании.",
  "Предпросмотр предстоящих событий в отдельном разделе.",
];

function CalendarIcon() {
  return (
    <svg aria-hidden="true" className="calendar-icon" fill="none" viewBox="0 0 24 24">
      <rect height="17" rx="3" width="18" x="3" y="4" />
      <path d="M8 2v4M16 2v4M3 9h18" />
    </svg>
  );
}

export default function App() {
  return (
    <>
      <header className="site-header">
        <div className="container header-content">
          <a aria-label="Calendar — на главную" className="brand" href="/">
            <CalendarIcon />
            <span>Calendar</span>
          </a>
          <nav aria-label="Основная навигация">
            <a className="nav-link" href="/event-types">
              Типы событий
            </a>
            <a className="nav-link" href="/events">
              Предстоящие события
            </a>
            <a className="nav-link" href="/book">
              Записаться
            </a>
          </nav>
        </div>
      </header>

      {window.location.pathname === "/event-types/new" ? (
        <EventTypeCreatePage />
      ) : window.location.pathname === "/event-types" ? (
        <EventTypesPage />
      ) : window.location.pathname === "/book" ? (
        <BookingPage />
      ) : window.location.pathname === "/events" ? (
        <UpcomingEventsPage />
      ) : (
        <main className="container hero">
          <section className="hero-content">
            <p className="eyebrow">Быстрая запись на звонок</p>
            <h1>Calendar</h1>
            <p className="hero-description">
              Один экран, понятные слоты, быстрая бронь. Выберите время и запишитесь на звонок без
              лишних шагов.
            </p>
            <a className="booking-button" href="/book">
              Записаться <span aria-hidden="true">→</span>
            </a>
          </section>

          <section aria-labelledby="features-title" className="features-card">
            <h2 id="features-title">Что доступно прямо сейчас</h2>
            <ul>
              {features.map((feature) => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>
          </section>
        </main>
      )}
    </>
  );
}
