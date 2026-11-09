import { useEffect, useState } from "react";

import { apiGetAvailability, apiListEventTypes } from "../api";
import type { Availability, EventType } from "../api";
import { moscowDate } from "../moscowDate";

export type SlotSelectionController = ReturnType<typeof useSlotSelection>;

export function useSlotSelection() {
  const [eventTypes, setEventTypes] = useState<EventType[]>([]);
  const [selectedTypeId, setSelectedTypeId] = useState("");
  const [selectedDate, setSelectedDate] = useState(() => moscowDate(1));
  const [availability, setAvailability] = useState<Availability | null>(null);
  const [availabilityAttempt, setAvailabilityAttempt] = useState(0);
  const [selectedStart, setSelectedStart] = useState<string | null>(null);
  const [loadError, setLoadError] = useState("");

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
        setLoadError("Не удалось загрузить типы событий");
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
        setLoadError("Не удалось загрузить доступность");
      }
    });
    return () => {
      active = false;
    };
  }, [availabilityAttempt, selectedDate, selectedTypeId]);

  function selectType(id: string) {
    setSelectedTypeId(id);
    setSelectedStart(null);
    setAvailability(null);
    setLoadError("");
  }

  function selectDate(date: string) {
    setSelectedDate(date);
    setSelectedStart(null);
    setAvailability(null);
  }

  function refresh() {
    setSelectedStart(null);
    setAvailability(null);
    setAvailabilityAttempt((value) => value + 1);
  }

  function reset() {
    setSelectedTypeId(eventTypes[0]?.id || "");
    setSelectedDate(moscowDate(1));
    setSelectedStart(null);
    setAvailability(null);
    setLoadError("");
    setAvailabilityAttempt((value) => value + 1);
  }

  return {
    availability,
    eventType,
    eventTypes,
    loadError,
    nextAvailableDay,
    refresh,
    reset,
    selectDate,
    selectType,
    selectedDate,
    selectedDayIsFull,
    selectedInterval,
    selectedStart,
    setSelectedStart,
    windowIsFull,
  };
}
