import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { apiCreateBooking, apiGetAvailability, apiListEventTypes } from "./api";
import type { Availability, Booking, EventType } from "./api";

type ContactErrors = {
  guestName?: string;
  guestEmail?: string;
};

function moscowDate(offset = 0) {
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Moscow",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  const date = new Date(`${today}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + offset);
  return date.toISOString().slice(0, 10);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    weekday: "short",
    timeZone: "Europe/Moscow",
  }).format(new Date(`${value}T12:00:00+03:00`));
}

function formatTime(value: string) {
  return value.slice(11, 16);
}

function validateContact(name: string, email: string): ContactErrors {
  const errors: ContactErrors = {};
  const normalizedName = name.trim();
  const normalizedEmail = email.trim();
  if (!normalizedName) {
    errors.guestName = "Введите имя";
  } else if (normalizedName.includes("\n") || normalizedName.includes("\r")) {
    errors.guestName = "Имя должно быть одной строкой";
  } else if (normalizedName.length > 100) {
    errors.guestName = "Имя не должно превышать 100 символов";
  }
  if (!normalizedEmail) {
    errors.guestEmail = "Введите email";
  } else if (normalizedEmail.length > 254) {
    errors.guestEmail = "Email не должен превышать 254 символа";
  } else {
    const parts = normalizedEmail.split("@");
    if (
      parts.length !== 2 ||
      !parts.every(Boolean) ||
      Array.from(normalizedEmail).some((character) => /\s/.test(character))
    ) {
      errors.guestEmail = "Введите корректный email";
    }
  }
  return errors;
}

function BookingSummary({
  eventType,
  date,
  startsAt,
  endsAt,
}: {
  eventType: EventType;
  date: string;
  startsAt: string;
  endsAt: string;
}) {
  return (
    <section aria-label="Сводка записи" className="booking-summary">
      <h2>{eventType.name}</h2>
      <p>{eventType.description}</p>
      <dl>
        <dt>Дата</dt>
        <dd>{formatDate(date)}</dd>
        <dt>Время</dt>
        <dd>
          {formatTime(startsAt)}–{formatTime(endsAt)}
        </dd>
        <dt>Длительность</dt>
        <dd>{eventType.durationMinutes} минут</dd>
        <dt>Часовой пояс</dt>
        <dd>Europe/Moscow</dd>
      </dl>
    </section>
  );
}

export default function BookingPage() {
  const [eventTypes, setEventTypes] = useState<EventType[]>([]);
  const [selectedTypeId, setSelectedTypeId] = useState("");
  const [selectedDate, setSelectedDate] = useState(() => moscowDate(1));
  const [availability, setAvailability] = useState<Availability | null>(null);
  const [availabilityAttempt, setAvailabilityAttempt] = useState(0);
  const [selectedStart, setSelectedStart] = useState<string | null>(null);
  const [view, setView] = useState<"select" | "confirm" | "success">("select");
  const [guestName, setGuestName] = useState("");
  const [guestEmail, setGuestEmail] = useState("");
  const [contactErrors, setContactErrors] = useState<ContactErrors>({});
  const [submitError, setSubmitError] = useState("");
  const [sending, setSending] = useState(false);
  const [keyReused, setKeyReused] = useState(false);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
  const nameInput = useRef<HTMLInputElement>(null);
  const emailInput = useRef<HTMLInputElement>(null);

  const eventType = eventTypes.find((item) => item.id === selectedTypeId);
  const selectedInterval = availability?.intervals.find(
    (interval) => interval.startsAt === selectedStart && interval.available,
  );
  const nextAvailableDay = availability?.days.find((day) => day.availableSlots > 0);
  const windowIsFull = availability?.days.every((day) => day.availableSlots === 0);
  const selectedDayIsFull = availability?.intervals.every((interval) => !interval.available);

  useEffect(() => {
    let active = true;
    void apiListEventTypes({ baseUrl: "" }).then(({ data }) => {
      if (!active) {
        return;
      }
      if (data) {
        setEventTypes(data);
        setSelectedTypeId((current) => current || data[0]?.id || "");
      } else {
        setSubmitError("Не удалось загрузить типы событий");
      }
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedTypeId) {
      return;
    }
    let active = true;
    void apiGetAvailability({
      baseUrl: "",
      path: { eventTypeId: selectedTypeId },
      query: { date: selectedDate },
    }).then(({ data }) => {
      if (!active) {
        return;
      }
      if (data) {
        setAvailability(data);
      } else {
        setSubmitError("Не удалось загрузить доступность");
      }
    });
    return () => {
      active = false;
    };
  }, [availabilityAttempt, selectedDate, selectedTypeId]);

  function startNewBooking() {
    setView("select");
    setSelectedTypeId(eventTypes[0]?.id || "");
    setSelectedDate(moscowDate(1));
    setSelectedStart(null);
    setAvailability(null);
    setGuestName("");
    setGuestEmail("");
    setContactErrors({});
    setSubmitError("");
    setBooking(null);
    setKeyReused(false);
    setIdempotencyKey(crypto.randomUUID());
  }

  async function submitBooking(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending || keyReused || !eventType || !selectedInterval) {
      return;
    }
    const errors = validateContact(guestName, guestEmail);
    setContactErrors(errors);
    if (errors.guestName) {
      nameInput.current?.focus();
      return;
    }
    if (errors.guestEmail) {
      emailInput.current?.focus();
      return;
    }

    setSending(true);
    setSubmitError("");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10_000);
    try {
      const { data, error } = await apiCreateBooking({
        baseUrl: "",
        body: {
          eventTypeId: eventType.id,
          startsAt: selectedInterval.startsAt,
          guestName: guestName.trim(),
          guestEmail: guestEmail.trim(),
        },
        headers: { "Idempotency-Key": idempotencyKey },
        signal: controller.signal,
      });
      if (data) {
        setBooking(data);
        setView("success");
      } else if (error?.code === "SLOT_CONFLICT") {
        setSubmitError("Это время уже занято");
        setSelectedStart(null);
        setAvailability(null);
        setView("select");
        setAvailabilityAttempt((value) => value + 1);
      } else if (error?.code === "IDEMPOTENCY_KEY_REUSED") {
        setSubmitError(error.message);
        setKeyReused(true);
      } else if (error?.code === "VALIDATION_ERROR") {
        const serverErrors: ContactErrors = {};
        const otherErrors: string[] = [];
        for (const item of error.fieldErrors) {
          if (item.field === "guestName") {
            serverErrors.guestName = item.message;
          } else if (item.field === "guestEmail") {
            serverErrors.guestEmail = item.message;
          } else {
            otherErrors.push(item.message);
          }
        }
        setContactErrors(serverErrors);
        if (serverErrors.guestName) {
          nameInput.current?.focus();
        } else if (serverErrors.guestEmail) {
          emailInput.current?.focus();
        }
        if (otherErrors.length > 0) {
          setSubmitError(otherErrors.join(" "));
        }
      } else {
        setSubmitError(
          "Не удалось подтвердить запись. Попробуйте ещё раз. Если ошибка повторится, вернитесь к выбору времени",
        );
      }
    } catch {
      setSubmitError(
        "Не удалось подтвердить запись. Попробуйте ещё раз. Если ошибка повторится, вернитесь к выбору времени",
      );
    } finally {
      clearTimeout(timeout);
      setSending(false);
    }
  }

  if (!eventType) {
    return (
      <main className="container booking-page">
        <h1>Запись на звонок</h1>
        <p role="status">Загрузка типов событий…</p>
        {submitError && <p role="alert">{submitError}</p>}
      </main>
    );
  }

  return (
    <main className="container booking-page">
      <h1>{view === "select" ? "Запись на звонок" : "Подтверждение записи"}</h1>
      {view === "select" && submitError && <p role="alert">{submitError}</p>}
      {view === "select" ? (
        <>
          <div aria-label="Тип события" className="booking-types" role="group">
            {eventTypes.map((item) => (
              <button
                aria-pressed={item.id === selectedTypeId}
                key={item.id}
                onClick={() => {
                  setSelectedTypeId(item.id);
                  setSelectedStart(null);
                  setAvailability(null);
                  setSubmitError("");
                }}
                type="button"
              >
                {item.name} · {item.durationMinutes} минут
              </button>
            ))}
          </div>
          <div className="booking-layout">
            <section className="booking-type-details">
              <h2>{eventType.name}</h2>
              <p>{eventType.description}</p>
              <p>{eventType.durationMinutes} минут</p>
              <p>Europe/Moscow</p>
            </section>
            <section>
              <h2>Выберите день</h2>
              <ul aria-label="Дни записи" className="booking-days">
                {availability?.days.map((day) => (
                  <li key={day.date}>
                    <button
                      aria-pressed={day.date === selectedDate}
                      onClick={() => {
                        setSelectedDate(day.date);
                        setSelectedStart(null);
                        setAvailability(null);
                      }}
                      type="button"
                    >
                      <span>{formatDate(day.date)}</span>
                      <span>{day.availableSlots} свободно</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h2>Выберите время</h2>
              {windowIsFull ? (
                <div role="status">
                  <p>В ближайшие 14 дней нет свободных слотов</p>
                  <p>Выберите другой тип события или вернитесь позже.</p>
                </div>
              ) : (
                selectedDayIsFull && (
                  <div role="status">
                    <p>На эту дату всё занято</p>
                    {nextAvailableDay && (
                      <button
                        onClick={() => {
                          setSelectedDate(nextAvailableDay.date);
                          setSelectedStart(null);
                          setAvailability(null);
                        }}
                        type="button"
                      >
                        Перейти к ближайшему свободному дню
                      </button>
                    )}
                  </div>
                )
              )}
              <ul aria-label="Интервалы" className="booking-intervals">
                {availability?.intervals.map((interval) => (
                  <li key={interval.startsAt}>
                    <button
                      aria-pressed={interval.startsAt === selectedStart}
                      disabled={!interval.available}
                      onClick={() => setSelectedStart(interval.startsAt)}
                      type="button"
                    >
                      {formatTime(interval.startsAt)}–{formatTime(interval.endsAt)}
                      {!interval.available && <span> Занято</span>}
                    </button>
                  </li>
                ))}
              </ul>
              <button disabled={!selectedInterval} onClick={() => setView("confirm")} type="button">
                Продолжить
              </button>
            </section>
          </div>
        </>
      ) : (
        <div className="confirmation-layout">
          <BookingSummary
            date={selectedDate}
            endsAt={view === "success" && booking ? booking.endsAt : selectedInterval?.endsAt || ""}
            eventType={view === "success" && booking ? booking.eventType : eventType}
            startsAt={
              view === "success" && booking ? booking.startsAt : selectedInterval?.startsAt || ""
            }
          />
          {view === "success" && booking ? (
            <section className="confirmation-form">
              <h2>Запись подтверждена</h2>
              <p>Вы записаны на звонок.</p>
              <p>{booking.guestName}</p>
              <p>{booking.guestEmail}</p>
              <button onClick={startNewBooking} type="button">
                Забронировать ещё
              </button>
            </section>
          ) : (
            <form className="confirmation-form" onSubmit={submitBooking}>
              <h2>Контактные данные</h2>
              {submitError && <p role="alert">{submitError}</p>}
              <label htmlFor="guest-name">Имя</label>
              <input
                aria-describedby={contactErrors.guestName ? "guest-name-error" : undefined}
                aria-invalid={Boolean(contactErrors.guestName)}
                disabled={sending || keyReused}
                id="guest-name"
                onChange={(event) => {
                  setGuestName(event.target.value);
                  if (contactErrors.guestName) {
                    setContactErrors(validateContact(event.target.value, guestEmail));
                  }
                }}
                ref={nameInput}
                value={guestName}
              />
              {contactErrors.guestName && <p id="guest-name-error">{contactErrors.guestName}</p>}
              <label htmlFor="guest-email">Email</label>
              <input
                aria-describedby={contactErrors.guestEmail ? "guest-email-error" : undefined}
                aria-invalid={Boolean(contactErrors.guestEmail)}
                disabled={sending || keyReused}
                id="guest-email"
                onChange={(event) => {
                  setGuestEmail(event.target.value);
                  if (contactErrors.guestEmail) {
                    setContactErrors(validateContact(guestName, event.target.value));
                  }
                }}
                ref={emailInput}
                type="text"
                value={guestEmail}
              />
              {contactErrors.guestEmail && <p id="guest-email-error">{contactErrors.guestEmail}</p>}
              {keyReused ? (
                <button onClick={startNewBooking} type="button">
                  Вернуться к выбору времени
                </button>
              ) : (
                <button disabled={sending} type="submit">
                  {sending
                    ? "Отправляем…"
                    : submitError
                      ? "Попробовать снова"
                      : "Подтвердить запись"}
                </button>
              )}
            </form>
          )}
        </div>
      )}
    </main>
  );
}
