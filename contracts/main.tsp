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

/** Бронирование слота в календаре. */
model Booking {
  /** Идентификатор бронирования. */
  id: string;

  /** Имя гостя. */
  guestName: string;

  /** Email гостя. */
  guestEmail: string;

  /** Начало слота в Europe/Moscow с точностью до минуты. */
  startsAt: string;

  /** Конец слота в Europe/Moscow с точностью до минуты. */
  endsAt: string;

  /** Забронированный тип события. */
  eventType: EventType;
}

/** Данные для создания бронирования. */
model BookingCreate {
  /** Идентификатор выбранного типа события. */
  eventTypeId: string;

  /** Начало слота в формате ГГГГ-ММ-ДДTЧЧ:ММ+03:00. */
  startsAt: string;

  /** Имя гостя. */
  guestName: string;

  /** Email гостя. */
  guestEmail: string;
}

/** Счётчик доступных слотов на календарный день. */
model AvailabilityDay {
  /** Дата в формате ГГГГ-ММ-ДД. */
  date: string;

  /** Количество свободных интервалов. */
  availableSlots: integer;
}

/** Интервал выбранного дня. */
model AvailabilityInterval {
  /** Начало интервала в Europe/Moscow. */
  startsAt: string;

  /** Окончание интервала в Europe/Moscow. */
  endsAt: string;

  /** Доступен ли интервал для бронирования. */
  available: boolean;
}

/** Доступность выбранного типа события. */
model Availability {
  /** Запрошенная дата. */
  date: string;

  /** Ровно 14 дней окна записи. */
  days: AvailabilityDay[];

  /** Все интервалы запрошенной даты. */
  intervals: AvailabilityInterval[];
}

/** Ошибка конкретного поля запроса. */
model FieldError {
  /** Имя поля или заголовка. */
  field: string;

  /** Машиночитаемый код ошибки. */
  code: string;

  /** Сообщение для пользователя. */
  message: string;
}

/** Общий формат ошибки API. */
model ApiError {
  /** Машиночитаемый код ошибки. */
  code: string;

  /** Сообщение для пользователя. */
  message: string;

  /** Ошибки полей запроса. */
  fieldErrors: FieldError[];
}

@error
model BadRequestError {
  @statusCode statusCode: 400;
  @body error: ApiError;
}

@error
model NotFoundError {
  @statusCode statusCode: 404;
  @body error: ApiError;
}

@error
model ConflictError {
  @statusCode statusCode: 409;
  @body error: ApiError;
}

/** Ошибка валидации параметров запроса. */
@error
model ValidationError {
  @statusCode statusCode: 422;
  @body error: ApiError;
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
  } | BadRequestError | ValidationError;

  /** Доступность типа события на выбранную дату и окно записи. */
  @get
  @route("/event-types/{eventTypeId}/availability")
  @tag("event-types")
  op getAvailability(
    @path eventTypeId: string,
    @query date: string,
  ): Availability | NotFoundError | ValidationError;

  /** Предстоящие бронирования в хронологическом порядке. */
  @get
  @route("/bookings")
  @tag("bookings")
  op listBookings(@query scope: "upcoming"): Booking[] | ValidationError;

  /** Создать бронирование. */
  @post
  @route("/bookings")
  @tag("bookings")
  op createBooking(
    @header("Idempotency-Key") idempotencyKey: string,
    @body booking: BookingCreate,
  ): {
    @statusCode
    statusCode: 201;

    @body
    booking: Booking;
  } | BadRequestError | NotFoundError | ConflictError | ValidationError;
}
