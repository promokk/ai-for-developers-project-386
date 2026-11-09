import "@typespec/http";

using TypeSpec.Http;

/** API сервиса «Календарь звонков»: бронирование слотов для звонков. */
@service(#{ title: "Call Calendar API" })
@server("http://127.0.0.1:8000", "Локальная разработка")
namespace CallCalendar;

/** Состояние сервиса. */
model Health {
  /** Текущий статус (`ok` — сервис работает). */
  status: string;
}

/** Тип события, доступный для бронирования. */
model EventType {
  /** Серверный идентификатор типа события. */
  id: string;

  /** Название типа события. */
  name: string;

  /** Необязательное описание типа события. */
  description: string | null;

  /** Длительность события в минутах. */
  durationMinutes: integer;
}

/** Данные для создания типа события. */
model EventTypeCreate {
  /** Название типа события. */
  name: string;

  /** Необязательное описание типа события. */
  description?: string | null;

  /** Длительность события: 30, 60, 90 или 120 минут. */
  durationMinutes: integer;
}

/** Ошибка конкретного поля запроса. */
model FieldError {
  /** Имя поля. */
  field: string;

  /** Машиночитаемый код ошибки. */
  code: string;

  /** Сообщение для пользователя. */
  message: string;
}

/** Согласованная ошибка API. */
model ApiError {
  /** Машиночитаемый код ошибки. */
  code: string;

  /** Сообщение для пользователя. */
  message: string;

  /** Ошибки полей в порядке проверки. */
  fieldErrors: FieldError[];
}

/** Бронирование слота в календаре. */
model Booking {
  /** Идентификатор бронирования. */
  id: string;

  /** Название звонка. */
  name: string;

  /** Начало слота. */
  startsAt: utcDateTime;

  /** Конец слота. */
  endsAt: utcDateTime;
}

/** Данные для создания бронирования. */
model BookingCreate {
  /** Название звонка. */
  name: string;

  /** Начало слота. */
  startsAt: utcDateTime;

  /** Конец слота. */
  endsAt: utcDateTime;
}

@route("/api")
namespace Api {
  /** Проверка доступности сервиса. */
  @get
  @route("/health")
  @tag("service")
  op health(): Health;

  /** Список типов событий в порядке создания. */
  @get
  @route("/event-types")
  @tag("event-types")
  op listEventTypes(): EventType[];

  /** Создать тип события. */
  @post
  @route("/event-types")
  @tag("event-types")
  op createEventType(@body eventType: EventTypeCreate): {
    @statusCode
    statusCode: 201;

    @body
    eventType: EventType;
  } | {
    @statusCode
    statusCode: 400;

    @body
    error: ApiError;
  } | {
    @statusCode
    statusCode: 422;

    @body
    error: ApiError;
  };

  /** Список всех бронирований. */
  @get
  @route("/bookings")
  @tag("bookings")
  op listBookings(): Booking[];

  /** Создать бронирование. */
  @post
  @route("/bookings")
  @tag("bookings")
  op createBooking(@body booking: BookingCreate): {
    @statusCode
    statusCode: 201;

    @body
    booking: Booking;
  };
}
