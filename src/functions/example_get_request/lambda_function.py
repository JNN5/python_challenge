from api_response_handler import api_response_handler
from .booking_input import BookingInput
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.logging.correlation_paths import API_GATEWAY_REST

from request_validation import parse_event
from util_helper import clean_data_fields
from models.example_booking import Booking

log = Logger()
tracer = Tracer()


@tracer.capture_lambda_handler
@api_response_handler
@log.inject_lambda_context(correlation_id_path=API_GATEWAY_REST, log_event=True)
def lambda_handler(event, context):
    booking_input = parse_event(event, BookingInput)
    bookings = find_relevant_bookings(booking_input)

    return map_to_output(bookings)


def find_relevant_bookings(booking_input: BookingInput) -> list[Booking]:
    if booking_input.capsule_id:
        bookings = Booking.query(booking_input.capsule_id)
    elif booking_input.company:
        bookings = Booking.company_startofweek_index.query(
            booking_input.company,
            Booking.start_of_week == booking_input.start_of_week,
            Booking.location == booking_input.location,
        )
    else:
        bookings = Booking.scan()

    return list(bookings)


def map_to_output(bookings: list[Booking]) -> list[dict]:
    booking_keys = ["company", "location", "capsule_id", "activity_date", "nric_sha"]

    output = []
    for booking in bookings:
        booking_dict = booking.attribute_values
        clean_data_fields(booking_dict, booking_keys)
        booking.decrypt()
        output.append(booking_dict)

    return output
