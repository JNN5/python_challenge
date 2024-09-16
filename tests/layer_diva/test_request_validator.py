from dataclasses import asdict, dataclass
from datetime import datetime
import importlib
import json
import pytest
from tests.layer_diva.helper_classes import Sample1, Statuz, Subsample1
from tests.utils import t
from freezegun import freeze_time


@pytest.fixture(scope="class")
def get_test_module():
    return importlib.import_module("src.layer_diva.python.request_validation")

@pytest.fixture(scope="class")
def get_api_module():
    return importlib.import_module("src.layer_diva.python.api_response_handler")

@freeze_time("2022-01-03")
class TestRequestValidator:
    def test_parse_event(self, get_test_module):
        # Given
        expected = Sample1(
            "myId",
            True,
            42,
            ["wow", "strings"],
            Subsample1("hello", {"a": [{"b": "c"}]}),
            {},
            datetime.now(),
            Statuz.FIRST,
            "2022-01-01"
        )
        event = {
            "body": json.dumps({
            "id": "myId",
            "active": True,
            "count": 42,
            "ids": ["wow", "strings"],
            "subclazz": {"hello": "hello", "nested_madness": {"a": [{"b": "c"}]}},
            "wow": {},
            "timestamp": "2022-01-03 00:00:00",
            "statuz": "first",
            "reg": "2022-01-01"
        })
        }

        # When
        result = get_test_module.parse_event(event, Sample1)

        # Then
        expected.__eq__(result)

    def test_fail_with_error(self, get_test_module, get_api_module):
        # Given
        event = {
            "body": json.dumps({})
        }

        # When / Then
        with pytest.raises(Exception):
            get_test_module.parse_event(event, Sample1)