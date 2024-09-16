# - - coding: utf-8 - -
"""
Created on 2021-09-01T09:30
"""
import pytest
from datetime import datetime
import importlib
import logging
import json
from responses import GET, POST
from freezegun import freeze_time
from tests.utils import t
from tests.layer_diva.helper_classes import Sample1, Statuz, Subsample1
import src.layer_diva.python.util_helper as util_helper
from src.layer_diva.python.models.example_booking import Booking




# Note: freeze_time freezes the datetime at UTC time. Thus @freeze_time("2022-01-03") actually freezes time at
# 2022-01-03 08:00:00 GMT+8
@freeze_time("2022-01-03")
class TestUtilHelper:
    def test_get_time_now_obj(self):
        response = util_helper.get_time_now_obj()
        assert isinstance(response, datetime)
        assert response.strftime("%Y-%m-%d") == "2022-01-03"

    def test_get_epoch_time_ms(self):
        response = util_helper.get_epoch_time_ms()
        assert isinstance(response, str)
        assert response == "1641168000000"

    def test_clean_data_fields(self):
        data_to_test = {"field1": "value1", "field2": "value2", "field3": "value3"}
        field_list = ["field1", "field2"]
        util_helper.clean_data_fields(data_to_test, field_list)
        assert data_to_test == {"field1": "value1", "field2": "value2"}

    def test_generate_random_pin(self):
        response = util_helper.generate_random_pin(10)
        assert len(response) == 10
        assert response.isupper()

        response = util_helper.generate_random_pin(15)
        assert len(response) == 15
        assert response.isupper()

    def test_to_dict(self):
        # Given
        sample = Sample1(
            "myId",
            True,
            42,
            ["wow", "strings"],
            Subsample1("hello", {"a": [{"b": "c"}]}),
            {},
            datetime.now(),
            Statuz.FIRST,
            "2022-01-01",
        )

        expected = {
            "id": "myId",
            "active": True,
            "count": 42,
            "ids": ["wow", "strings"],
            "subclazz": {"hello": "hello", "nested_madness": {"a": [{"b": "c"}]}},
            "wow": {},
            "timestamp": "2022-01-03 00:00:00",
            "statuz": "first",
            "reg": "2022-01-01",
        }

        # When
        result = util_helper.to_dict(sample)

        # Then
        t.assertDictEqual(result, expected)
