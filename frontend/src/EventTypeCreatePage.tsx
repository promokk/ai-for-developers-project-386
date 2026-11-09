import { useEffect, useRef, useState } from "react";
import type { FormEvent, MouseEvent } from "react";

import { apiCreateEventType } from "./api";

type FieldName = "name" | "description" | "durationMinutes";
type FieldErrors = Partial<Record<FieldName, string>>;

export default function EventTypeCreatePage() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [durationMinutes, setDurationMinutes] = useState("30");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [failed, setFailed] = useState(false);
  const [pending, setPending] = useState(false);
  const pendingRef = useRef(false);
  const allowLeaveRef = useRef(false);
  const nameRef = useRef<HTMLInputElement>(null);
  const descriptionRef = useRef<HTMLTextAreaElement>(null);
  const durationRef = useRef<HTMLSelectElement>(null);
  const dirty = name !== "" || description !== "" || durationMinutes !== "30";

  useEffect(() => {
    function confirmLeave(event: BeforeUnloadEvent) {
      if (dirty && !allowLeaveRef.current) {
        event.preventDefault();
        event.returnValue = true;
      }
    }
    window.addEventListener("beforeunload", confirmLeave);
    return () => window.removeEventListener("beforeunload", confirmLeave);
  }, [dirty]);

  function handleCancel(event: MouseEvent<HTMLAnchorElement>) {
    if (!dirty) {
      return;
    }
    if (window.confirm("Несохранённые данные будут потеряны. Покинуть страницу?")) {
      allowLeaveRef.current = true;
    } else {
      event.preventDefault();
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pendingRef.current) {
      return;
    }
    pendingRef.current = true;
    setPending(true);
    setFailed(false);
    setFieldErrors({});
    try {
      const { data, error, response } = await apiCreateEventType({
        baseUrl: "",
        body: {
          name,
          description,
          durationMinutes: Number(durationMinutes),
        },
      });
      if (data) {
        allowLeaveRef.current = true;
        window.location.assign("/event-types?created=1");
        return;
      }
      if (response?.status === 422 && error) {
        const nextErrors: FieldErrors = {};
        for (const fieldError of error.fieldErrors) {
          if (
            fieldError.field === "name" ||
            fieldError.field === "description" ||
            fieldError.field === "durationMinutes"
          ) {
            nextErrors[fieldError.field] = fieldError.message;
          }
        }
        setFieldErrors(nextErrors);
        const firstField = error.fieldErrors[0]?.field;
        if (firstField === "name") {
          nameRef.current?.focus();
        } else if (firstField === "description") {
          descriptionRef.current?.focus();
        } else if (firstField === "durationMinutes") {
          durationRef.current?.focus();
        }
        return;
      }
      setFailed(true);
    } catch {
      setFailed(true);
    } finally {
      pendingRef.current = false;
      setPending(false);
    }
  }

  return (
    <main className="container event-types-page">
      <h1>Новый тип события</h1>
      {failed && <p role="alert">Не удалось создать тип события. Попробуйте ещё раз</p>}
      <form noValidate onSubmit={(event) => void handleSubmit(event)}>
        <div>
          <label htmlFor="event-type-name">Название</label>
          <input
            aria-describedby={fieldErrors.name ? "event-type-name-error" : undefined}
            aria-invalid={Boolean(fieldErrors.name)}
            id="event-type-name"
            onChange={(event) => setName(event.target.value)}
            ref={nameRef}
            value={name}
          />
          {fieldErrors.name && <p id="event-type-name-error">{fieldErrors.name}</p>}
        </div>
        <div>
          <label htmlFor="event-type-description">Описание</label>
          <textarea
            aria-describedby={fieldErrors.description ? "event-type-description-error" : undefined}
            aria-invalid={Boolean(fieldErrors.description)}
            id="event-type-description"
            onChange={(event) => setDescription(event.target.value)}
            ref={descriptionRef}
            value={description}
          />
          {fieldErrors.description && (
            <p id="event-type-description-error">{fieldErrors.description}</p>
          )}
        </div>
        <div>
          <label htmlFor="event-type-duration">Длительность</label>
          <select
            aria-describedby={fieldErrors.durationMinutes ? "event-type-duration-error" : undefined}
            aria-invalid={Boolean(fieldErrors.durationMinutes)}
            id="event-type-duration"
            onChange={(event) => setDurationMinutes(event.target.value)}
            ref={durationRef}
            value={durationMinutes}
          >
            <option value="30">30 минут</option>
            <option value="60">60 минут</option>
            <option value="90">90 минут</option>
            <option value="120">120 минут</option>
          </select>
          {fieldErrors.durationMinutes && (
            <p id="event-type-duration-error">{fieldErrors.durationMinutes}</p>
          )}
        </div>
        <button disabled={pending} type="submit">
          Создать тип события
        </button>
        <a href="/event-types" onClick={handleCancel}>
          Отмена
        </a>
      </form>
    </main>
  );
}
