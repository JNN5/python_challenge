from dataclasses import asdict, dataclass
from enum import Enum
import datetime
import time
import string
import secrets
from typing import Any, List, Optional, Tuple
from uuid import UUID
from pynamodb.models import Model
import boto3
import util_constants

DDB_CLIENT = boto3.client("dynamodb")
DDB_RES = boto3.resource("dynamodb")
SSM = boto3.client("ssm")
DATE_TIME_TO_DICT_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_time_now_obj():
    """Helper to get formatted time now in object"""
    return datetime.datetime.today() + datetime.timedelta(hours=8)

def get_epoch_time_ms():
    """Helper to get epoch time now"""
    time_now_ms = int(time.time() * 1000)  # epoch in milliseconds
    return str(time_now_ms)

def get_dt_now_str():
    """ Helper to get formatted time now as str for dt attributes"""
    return get_time_now_obj().strftime(util_constants.DATETIME_FORMAT)

def get_ttl(days):
    """ Helper to get TTL epoch time """
    return int((get_time_now_obj() + datetime.timedelta(days=days)).timestamp())


def clean_data_fields(data, field_list):
    """Clean up by returning only wanted field_list from the data_list
    Args:
        data: DICT, data to be clean up
        field_list: LIST, list of fields that should be returned
    """
    for k, v in list(data.items()):
        if k not in field_list:
            data.pop(k)
        elif isinstance(v, datetime.datetime):
            data[k] = v.strftime(util_constants.DATETIME_FORMAT)


def generate_random_pin(length):
    """Generate random pin (Uppercase alphabets + digits only) based on length
    Args:
        length: INT, length of the generated pin
    """
    pin_criteria = string.ascii_uppercase + string.digits
    random_pin = "".join(secrets.choice(pin_criteria) for _ in range(length))

    return random_pin


def setup_model(model: Model, table_name: Optional[str] = None):
    if table_name is not None:
        model.Meta.table_name = table_name
    if not model.exists():
        model.create_table(wait=True, billing_mode="PAY_PER_REQUEST")
    return model

def to_dict(obj: dataclass):
    return asdict(obj, dict_factory=_dict_factory)

def _dict_factory(data: List[Tuple[str, Any]]):
    return {
        field: _format_dataclass_field(value)
        for field, value in data
        }

def _format_dataclass_field(value):
    if isinstance(value, datetime.datetime):
        return value.strftime(DATE_TIME_TO_DICT_FORMAT)
    elif isinstance(value, UUID):
        return str(value)
    elif isinstance(value, Enum):
        return value.value
    else:
        return value

def get_ssm_param(param_name, encryption=False):
    ssm_response = SSM.get_parameter(
            Name=param_name, WithDecryption=encryption
        )
    return ssm_response.get("Parameter", {}).get("Value")