import { useRef } from "react";

import type { BookingSubmissionController } from "./useBookingSubmission";

export function ContactForm({
  form,
  onRestart,
}: {
  form: BookingSubmissionController;
  onRestart: () => void;
}) {
  const nameInput = useRef<HTMLInputElement>(null);
  const emailInput = useRef<HTMLInputElement>(null);

  return (
    <form
      className="confirmation-form"
      onSubmit={(event) => form.submitBooking(event, nameInput, emailInput)}
    >
      <h2>Контактные данные</h2>
      {form.submitError && <p role="alert">{form.submitError}</p>}
      <label htmlFor="guest-name">Имя</label>
      <input
        aria-describedby={form.contactErrors.guestName ? "guest-name-error" : undefined}
        aria-invalid={Boolean(form.contactErrors.guestName)}
        disabled={form.sending || form.keyReused}
        id="guest-name"
        onChange={(event) => form.changeName(event.target.value)}
        ref={nameInput}
        value={form.guestName}
      />
      {form.contactErrors.guestName && <p id="guest-name-error">{form.contactErrors.guestName}</p>}
      <label htmlFor="guest-email">Email</label>
      <input
        aria-describedby={form.contactErrors.guestEmail ? "guest-email-error" : undefined}
        aria-invalid={Boolean(form.contactErrors.guestEmail)}
        disabled={form.sending || form.keyReused}
        id="guest-email"
        onChange={(event) => form.changeEmail(event.target.value)}
        ref={emailInput}
        type="text"
        value={form.guestEmail}
      />
      {form.contactErrors.guestEmail && (
        <p id="guest-email-error">{form.contactErrors.guestEmail}</p>
      )}
      {form.keyReused ? (
        <button onClick={onRestart} type="button">
          Вернуться к выбору времени
        </button>
      ) : (
        <button disabled={form.sending} type="submit">
          {form.sending
            ? "Отправляем…"
            : form.submitError
              ? "Попробовать снова"
              : "Подтвердить запись"}
        </button>
      )}
    </form>
  );
}
