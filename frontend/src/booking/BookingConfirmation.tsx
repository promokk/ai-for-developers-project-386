import type { AvailabilityInterval, Booking, EventType } from "../api";
import { ContactForm } from "./ContactForm";
import { formatDate, formatTime } from "./format";
import type { BookingSubmissionController } from "./useBookingSubmission";

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

export function BookingConfirmation({
  booking,
  date,
  eventType,
  form,
  onRestart,
  selectedInterval,
}: {
  booking: Booking | null;
  date: string;
  eventType: EventType;
  form: BookingSubmissionController;
  onRestart: () => void;
  selectedInterval: AvailabilityInterval | undefined;
}) {
  return (
    <div className="confirmation-layout">
      <BookingSummary
        date={date}
        endsAt={booking ? booking.endsAt : selectedInterval?.endsAt || ""}
        eventType={booking ? booking.eventType : eventType}
        startsAt={booking ? booking.startsAt : selectedInterval?.startsAt || ""}
      />
      {booking ? (
        <section className="confirmation-form">
          <h2>Запись подтверждена</h2>
          <p>Вы записаны на звонок.</p>
          <p>{booking.guestName}</p>
          <p>{booking.guestEmail}</p>
          <button onClick={onRestart} type="button">
            Забронировать ещё
          </button>
        </section>
      ) : (
        <ContactForm form={form} onRestart={onRestart} />
      )}
    </div>
  );
}
