from models.example_booking import Booking
import pytest

mock_booking_1 = Booking(
    capsule_id="123456",
    activity_date="2022-01-05",
    start_of_week="2022-01-03",
    company="CAG",
    location="Airport",
    nric_sha="1d83712192a87df9531606e77f5c57cb111a359b522a69405497ba98001057bf",
)

mock_booking_2 = Booking(
    capsule_id="555555",
    activity_date="2022-01-05",
    start_of_week="2022-01-03",
    company="CAG",
    location="Airport",
    nric_sha="1d83712192a87df9531606e77f5c57cb111a359b522a69405497ba98001057bf",
)


def save_sample_bookings():
    mock_booking_1.encrypt(pytest.kms_key_id).save()
    mock_booking_2.encrypt(pytest.kms_key_id).save()


response = [
    {
        "activity_date": "2022-01-05",
        "capsule_id": "123456",
        "company": "CAG",
        "location": "Airport",
        "nric_sha": "1d83712192a87df9531606e77f5c57cb111a359b522a69405497ba98001057bf",
    },
    {
        "activity_date": "2022-01-05",
        "capsule_id": "555555",
        "company": "CAG",
        "location": "Airport",
        "nric_sha": "1d83712192a87df9531606e77f5c57cb111a359b522a69405497ba98001057bf",
    },
    {
        "activity_date": "2022-01-05",
        "capsule_id": "888888",
        "company": "CAG",
        "location": "Airport",
        "nric_sha": "1d83712192a87df9531606e77f5c57cb111a359b522a69405497ba98001057bf",
    },
]

valid_request = {"company": "CAG", "start_of_week": "2022-01-03", "location": "Airport"}

valid_response = {"company": "CAG", "start_of_week": "2022-01-03", "location": "Airport"}