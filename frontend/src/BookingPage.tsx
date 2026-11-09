import { useState } from "react";

import type { Booking } from "./api";
import { BookingConfirmation } from "./booking/BookingConfirmation";
import { SlotSelection } from "./booking/SlotSelection";
import { useBookingSubmission } from "./booking/useBookingSubmission";
import { useSlotSelection } from "./booking/useSlotSelection";

export default function BookingPage() {
  const [view, setView] = useState<"select" | "confirm" | "success">("select");
  const [booking, setBooking] = useState<Booking | null>(null);
  const selection = useSlotSelection();
  const submission = useBookingSubmission({
    eventType: selection.eventType,
    selectedInterval: selection.selectedInterval,
    onConflict: () => {
      selection.refresh();
      setView("select");
    },
    onSuccess: (created) => {
      setBooking(created);
      setView("success");
    },
  });

  function startNewBooking() {
    setView("select");
    setBooking(null);
    selection.reset();
    submission.reset();
  }

  const error = submission.submitError || selection.loadError;
  if (!selection.eventType) {
    return (
      <main className="container booking-page">
        <h1>Запись на звонок</h1>
        <p role="status">Загрузка типов событий…</p>
        {error && <p role="alert">{error}</p>}
      </main>
    );
  }

  return (
    <main className="container booking-page">
      <h1>{view === "select" ? "Запись на звонок" : "Подтверждение записи"}</h1>
      {view === "select" && error && <p role="alert">{error}</p>}
      {view === "select" ? (
        <SlotSelection
          onContinue={() => setView("confirm")}
          onTypeChange={submission.clearSubmitError}
          selection={selection}
        />
      ) : (
        <BookingConfirmation
          booking={view === "success" ? booking : null}
          date={selection.selectedDate}
          eventType={selection.eventType}
          form={submission}
          onRestart={startNewBooking}
          selectedInterval={selection.selectedInterval}
        />
      )}
    </main>
  );
}
