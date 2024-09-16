from dataclasses import Field, dataclass, fields
import re
import datetime
import boto3
import json
from api_response_handler import BadRequest
from aws_lambda_powertools import Logger
import util_constants

# LOGGER
log = Logger()

COGNITO_CLIENT = boto3.client("cognito-idp")
SSM = boto3.client("ssm")


def get_regex_dict():
    """Method to return all regex dict
    Returns:
        regex_dict: DICT, regex dictionary
    """
    regex_dict = {
        "location": util_constants.TEXT_REGEX % (300),
        "company": util_constants.TEXT_REGEX % (300),
        "capsule_id": util_constants.TEXT_REGEX % (300),
        "activity_date": util_constants.DATE_REGEX,
        "start_of_week": util_constants.DATE_REGEX,
        "booking_status": r"^(%s|%s)$"
        % (util_constants.SAMPLE_STATUS_ACTIVE, util_constants.SAMPLE_STATUS_INACTIVE),
        "contact_num": r"^[6,8,9][0-9]{7}$",
    }

    for k, value in regex_dict.items():
        if (
            value != "NA"
            and value != util_constants.LIST_REGEX
            and value != util_constants.OBJECT_REGEX
            and value != util_constants.OBJECT_LIST_REGEX
        ):
            regex_dict[k] = re.compile(value, re.IGNORECASE)

    return regex_dict


def process_request(
    request_dict,
    validation_method,
    business_logic_method,
    cors=None,
    allowed_roles=None,
):
    """Method validates request data, and processes it if data has passed validation
    Serves as an entry point of the class.
    Args:
        request_dict: DICT, The raw request
        validation_method: FUNC, validation function
        business_logic_method: FUNC, main biz logic function
        cors: STR, CORS to be assigned to header
        allowed_roles: LIST, list of allowed cognito roles. OPTIONAL: If not passing, all roles are allowed.
    Returns:
        self.response : DICT, {'statusCode':200, 'headers': ${headers},
                                'isBase64Encoded' : False, 'body' : ${data}}
    """
    start_dt = datetime.datetime.now()

    # set response headers
    # Response
    response = {i: "" for i in ["isBase64Encoded", "headers", "statusCode", "body"]}
    response["isBase64Encoded"] = False
    response["headers"] = _generate_sec_header(cors)

    try:
        # get request body for processing
        request_body = request_dict.get("body", {})
        request_headers = request_dict.get("headers", {})

        success, request_body = _load_request_json(request_body)

        # 1. validate data
        if success and validation_method(request_body):
            valid = True
            cred_data = {}
            if allowed_roles:
                valid, cred_data = _validate_token_info(
                    allowed_roles, request_headers.get("Authorization", "")
                )

            if not valid:
                response["statusCode"] = 401
                response["body"] = "User role unauthorized."
            else:
                # 2. process request if request passes validation
                # process validated data and build response data
                # integrate with business layer
                if allowed_roles:
                    response_data = business_logic_method(
                        validated_data=request_body, cred_data=cred_data
                    )
                else:
                    response_data = business_logic_method(validated_data=request_body)

                if response_data is not None:

                    # data was found, processing is OK and data is found
                    response["statusCode"] = 200
                    response["body"] = json.dumps(response_data)

                else:
                    # data was found, processing is OK and data is not found
                    response["statusCode"] = 404
                    response["body"] = "Data not found."

        else:
            # request failed validation
            response["statusCode"] = 400
            response["body"] = "Invalid request data provided."

    except Exception as e:
        # server side error
        response["statusCode"] = 500
        response["body"] = "Server side error while processing request."
        log.error("ERROR processing request: %s", e)

    delta = datetime.datetime.now() - start_dt
    log.info("RESP: code %s, execution %s", response["statusCode"], delta)
    return response


# REQUEST validation
def validate_keys(request_body, expected_attr, optional_attr):
    """Method to validate expected and optional keys for each dict
    Args:
        request_body: DICT, dictionary to be validated
        expected_attr: LIST, list of expected attributes
        optional_attr: LIST, list of optional attributes
    Returns:
        valid: BOOL, whether validation passed
    """
    if not _required_validation(request_body, expected_attr, optional_attr):
        return False

    regex_dict = get_regex_dict()
    for k in request_body.keys():
        if regex_dict[k] == util_constants.NA_REGEX:
            continue
        if regex_dict[k] == util_constants.LIST_REGEX:
            for item in request_body[k]:
                if not _regex_validation(regex_dict[k + "_list"], str(item), k):
                    return False
        elif regex_dict[k] == util_constants.OBJECT_REGEX:
            if not _validate_object(request_body[k], regex_dict):
                return False
        elif regex_dict[k] == util_constants.OBJECT_LIST_REGEX:
            if not _validate_object_list(request_body[k], regex_dict):
                return False
        elif not _regex_validation(regex_dict[k], str(request_body[k]), k):
            return False

    return True


def _required_validation(request_body, expected_attr, optional_attr) -> bool:
    required_data_msg = "REQUEST: unsupported request body received: '%s'."
    if set(request_body.keys()).issuperset(expected_attr):
        if not set(request_body.keys()).issubset(optional_attr + expected_attr):
            log.warning(required_data_msg, request_body.keys())
            return False
    else:
        log.warning(required_data_msg, request_body.keys())
        return False

    return True


def _validate_object(object_list: list, regex_dict: dict) -> bool:
    for k in object_list.keys():
        if not _regex_validation(regex_dict.get(k, None), str(object_list[k]), k):
            return False
    return True


def _validate_object_list(object_list: list, regex_dict: dict) -> bool:
    for item in object_list:
        for inner_k in item.keys():
            if not _regex_validation(
                regex_dict.get(inner_k, None), str(item[inner_k]), inner_k
            ):
                return False
    return True


def _regex_validation(
    regex_str: str or None, string_to_be_validated: str, key_name: str
) -> bool:
    unsupported_data_msg = (
        "REQUEST: unsupported request body received. Invalid data provided for '%s'."
    )
    if regex_str is None:
        log.warning(unsupported_data_msg, key_name)
        return False

    single_value = re.findall(regex_str, string_to_be_validated)
    if single_value == []:
        # invalid data is returned
        log.warning(unsupported_data_msg, key_name)
        return False
    return True


def _validate_token_info(allowed_roles, access_token):
    """Method to validate token and return credential information.
    Args:
        allowed_roles: LIST, list of roles allowed to call this API
        access_token: STR, access token
    Returns:
        valid: BOOL, whether is authorized
        cred_data: DICT, data from cognito
        {
            "role": "supervisor",
            "company": "Certis",
            "username": "rrt_alvin_super@yopmail.com",
            "username_sha": "xxxx"
        }
    """
    cred_data = {}

    try:
        if access_token != "":
            response = COGNITO_CLIENT.get_user(AccessToken=access_token)

            cred_data = {}

            # Processing of token
            for attr in response.get("UserAttributes", []):
                cred_data[attr["Name"]] = attr["Value"]

            ssm_response = SSM.get_parameter(
                Name="cognito_user_pool_id", WithDecryption=False
            )
            cognito_user_pool_id = ssm_response.get("Parameter", {}).get("Value")

            # Processing of Role
            group_response = COGNITO_CLIENT.admin_list_groups_for_user(
                Username=response["Username"], UserPoolId=cognito_user_pool_id
            )
            group_info = next(iter(group_response.get("Groups", [])), {})
            cred_data["role"] = group_info.get("GroupName", "")
            log.info(
                "AUTH: User found with cognito_username: %s, role: %s."
                % (response["Username"], cred_data["role"])
            )

            if cred_data["role"] not in allowed_roles:
                log.warning("AUTH: Not authorized to proceed.")
                return False, {}

            return True, cred_data

    except Exception as e:
        log.error("AUTH: Access token failed: %s", e)

    return False, {}


def _load_request_json(request_body):
    """Convert request body from string to JSON DICT, if not a valid JSON, should return False
    Args:
        request_body: STR, request body in string
    Returns:
        success: BOOL, whether the transformation is succeeded
        request_body: DICT, transformed request body
    """
    try:
        request_body = json.loads(request_body)
    except Exception as e:
        log.error("Unable to transform request body: %s", e)
        return False, {}
    return True, request_body


def _generate_sec_header(cors=None):
    """Generate standard security header
    Args:
        cors: STR, if cors exists then return
    Returns:
        headers: DICT, response headers
    """
    headers = {}
    headers["Content-Type"] = "application/json"
    headers["X-Content-Type-Options"] = "nosniff"
    headers["Strict-Transport-Security"] = "max-age=16070400; includeSubDomains"
    headers["X-XSS-Protection"] = "1; mode=block"
    headers["X-Frame-Options"] = "SAMEORIGIN"
    headers["Cache-Control"] = "no-store"
    headers["content-security-policy"] = "default-src 'self'; object-src 'none';"
    headers["x-permitted-cross-domain-policies"] = "master-only"
    if cors is not None:
        headers["Access-Control-Allow-Origin"] = cors
    return headers


def parse_event(event: dict, clazz: dataclass):
    if event.get("body"):
        body = _parse_event_body(event)
    else:
        body = event
    required_fields = _get_required_class_fields(clazz)
    all_fields = _get_all_class_fields(clazz)
    if not all(elem in list(body.keys()) for elem in required_fields):
        raise BadRequest(
            f"{event} does not contain all of these fields {required_fields}"
        )
    elif any(elem not in all_fields for elem in list(body.keys())):
        raise BadRequest(
            f"{event} contains fields that are not expected {all_fields}"
        )
    try: 
        return clazz(*[_parse_field_from_event(f, body) for f in fields(clazz)])
    except Exception as e:
        raise BadRequest(f"Unable to parse event: {event}. Error: {e}")


def _parse_field_from_event(f: Field, body: dict):
    value = body.get(f.name, None)
    regex = f.metadata.get("regex", None)
    date_format = f.metadata.get("date_format", None)
    if value is None:
        return None
    elif date_format is not None:
        return datetime.datetime.strptime(value, date_format)
    elif regex is not None and re.findall(regex, value) == []:
        raise BadRequest(
            f"{value} is not a valid format for field {f.name}. It has to conform to this regex: {regex}"
        )
    else:
        return value


def _get_required_class_fields(clazz: dataclass):
    # We want to filter out Optional types.
    # Optional means a Union of some type with a None type
    # Hence, we can check that the type definition does not include a None type
    return [
        x.name
        for x in fields(clazz)
        if hasattr(x.type, "__args__") == False or type(None) not in x.type.__args__
    ]


def _get_all_class_fields(clazz: dataclass):
    return [x.name for x in fields(clazz)]


def _parse_event_body(event: dict):
    try:
        return json.loads(event.get("body"))
    except Exception as e:
        raise BadRequest(
            f"Unexpected format of input event: {event}. Parsing failed due to error: {e}"
        )
