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
