import pytest
import json
from responses import GET, POST
from freezegun import freeze_time

from tests.utils import create_test_request, t
from src.functions.example_get_request.lambda_function import lambda_handler
from . import mock_data

# Note: freeze_time freezes the datetime at UTC time. Thus @freeze_time("2022-01-03") actually freezes time at
# 2022-01-03 08:00:00 GMT+8
@freeze_time("2022-01-03")
class TestGetBookings:
    @pytest.mark.parametrize(
        "test_body, expected_output",
        [
            ({"xxxxx": "2023-01-04"}, 400),
            (None, 500),
        ],
    )
    def test_bad_request_body(self, test_body, expected_output, lambda_context):
        request = create_test_request(test_body)
        response = lambda_handler(request, lambda_context)

        assert response["statusCode"] == expected_output

    def test_valid(self, lambda_context):
        request = {
            "body": json.dumps(
                {"company": "CAG", "start_of_week": "2022-01-03", "location": "Airport"}
            ),
        }

        response = lambda_handler(request, lambda_context)
        body = response.get("body", {})
        if isinstance(response, str):
            body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert len(body) > 0

    def test_capsule_valid(self, lambda_context):
        request = create_test_request({"capsule_id": "888888"})

        response = lambda_handler(request, lambda_context)
        body = response.get("body", {})
        if isinstance(response, str):
            body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert len(body) > 0

    def test_scan(self, lambda_context):
        mock_data.save_sample_bookings()
        request = create_test_request({})

        response = lambda_handler(request, lambda_context)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        t.assertCountEqual(body, mock_data.response)


    def test_mock_response(self, mock_responses):
        mock_responses.add(
            POST, url="http://www.google.com", status=404
        )  # queue a response
        import requests

        r = requests.post("http://www.google.com")
        assert r.status_code == 404
