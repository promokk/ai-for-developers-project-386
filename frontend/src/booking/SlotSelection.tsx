import { formatDate, formatTime } from "./format";
import type { SlotSelectionController } from "./useSlotSelection";

export function SlotSelection({
  onContinue,
  onTypeChange,
  selection,
}: {
  onContinue: () => void;
  onTypeChange: () => void;
  selection: SlotSelectionController;
}) {
  const { availability, eventType } = selection;
  if (!eventType) {
    return null;
  }

  return (
    <>
      <div aria-label="Тип события" className="booking-types" role="group">
        {selection.eventTypes.map((item) => (
          <button
            aria-pressed={item.id === eventType.id}
            key={item.id}
            onClick={() => {
              selection.selectType(item.id);
              onTypeChange();
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
                  aria-pressed={day.date === selection.selectedDate}
                  onClick={() => selection.selectDate(day.date)}
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
          {selection.windowIsFull ? (
            <div role="status">
              <p>В ближайшие 14 дней нет свободных слотов</p>
              <p>Выберите другой тип события или вернитесь позже.</p>
            </div>
          ) : (
            selection.selectedDayIsFull && (
              <div role="status">
                <p>На эту дату всё занято</p>
                {selection.nextAvailableDay && (
                  <button
                    onClick={() => selection.selectDate(selection.nextAvailableDay!.date)}
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
                  aria-pressed={interval.startsAt === selection.selectedStart}
                  disabled={!interval.available}
                  onClick={() => selection.setSelectedStart(interval.startsAt)}
                  type="button"
                >
                  {formatTime(interval.startsAt)}–{formatTime(interval.endsAt)}
                  {!interval.available && <span> Занято</span>}
                </button>
              </li>
            ))}
          </ul>
          <button disabled={!selection.selectedInterval} onClick={onContinue} type="button">
            Продолжить
          </button>
        </section>
      </div>
    </>
  );
}
