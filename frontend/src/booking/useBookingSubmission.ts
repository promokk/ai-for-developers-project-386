import { useRef, useState } from "react";
import type { FormEvent, RefObject } from "react";

import { apiCreateBooking } from "../api";
import type { AvailabilityInterval, Booking, EventType } from "../api";

type ContactErrors = {
  guestName?: string;
  guestEmail?: string;
};

export type BookingSubmissionController = ReturnType<typeof useBookingSubmission>;

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
      Array.from(normalizedEmail).some((character) => /[\p{Cc}\s]/u.test(character))
    ) {
      errors.guestEmail = "Введите корректный email";
    }
  }
  return errors;
}

export function useBookingSubmission({
  eventType,
  selectedInterval,
  onConflict,
  onSuccess,
}: {
  eventType: EventType | undefined;
  selectedInterval: AvailabilityInterval | undefined;
  onConflict: () => void;
  onSuccess: (booking: Booking) => void;
}) {
  const [guestName, setGuestName] = useState("");
  const [guestEmail, setGuestEmail] = useState("");
  const [contactErrors, setContactErrors] = useState<ContactErrors>({});
  const [submitError, setSubmitError] = useState("");
  const [sending, setSending] = useState(false);
  const sendingRef = useRef(false);
  const [keyReused, setKeyReused] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());

  async function submitBooking(
    event: FormEvent<HTMLFormElement>,
    nameInput: RefObject<HTMLInputElement | null>,
    emailInput: RefObject<HTMLInputElement | null>,
  ) {
    event.preventDefault();
    if (sendingRef.current || sending || keyReused || !eventType || !selectedInterval) {
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

    sendingRef.current = true;
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
        onSuccess(data);
      } else if (error?.code === "SLOT_CONFLICT") {
        setSubmitError("Это время уже занято");
        onConflict();
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
      sendingRef.current = false;
      setSending(false);
    }
  }

  function changeName(value: string) {
    setGuestName(value);
    if (contactErrors.guestName) {
      setContactErrors(validateContact(value, guestEmail));
    }
  }

  function changeEmail(value: string) {
    setGuestEmail(value);
    if (contactErrors.guestEmail) {
      setContactErrors(validateContact(guestName, value));
    }
  }

  function reset() {
    setGuestName("");
    setGuestEmail("");
    setContactErrors({});
    setSubmitError("");
    setKeyReused(false);
    setIdempotencyKey(crypto.randomUUID());
  }

  return {
    changeEmail,
    changeName,
    clearSubmitError: () => setSubmitError(""),
    contactErrors,
    guestEmail,
    guestName,
    keyReused,
    reset,
    sending,
    submitBooking,
    submitError,
  };
}
