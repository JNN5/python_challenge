# -*- coding: utf-8 -*-
"""
Created on 2021-09-01T09:30
"""
from dataclasses import dataclass, field
from functools import reduce
import importlib
import re
from typing import Optional, Dict, List
import pytest
import os
import json
import boto3
import uuid
import base64
from requests_mock import Mocker
from pathlib import Path
import responses
from tests.utils import load_file
from src.layer_diva.python.appconfig_manager import ConfigException
from encryption_client import EncryptionClient


@pytest.fixture(autouse=True, scope="session")
def A():
    # Do not change method name, we need this to run first in the test session
    from moto import mock_aws

    mock_aws = mock_aws()
    mock_aws.start()
    yield
    mock_aws.stop()


@pytest.fixture(autouse=True, scope="session")
def aws_credentials():
    # env for testing
    os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-1"
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["POWERTOOLS_SERVICE_NAME"] = "Test-Service"
    os.environ["POWERTOOLS_METRICS_NAMESPACE"] = "Test-Metric-Namespace"


@pytest.fixture
def lambda_context():
    @dataclass
    class LambdaContext:
        function_name: str = "test"
        memory_limit_in_mb: int = 128
        invoked_function_arn: str = (
            "arn:aws:lambda:ap-southeast-1:809313241:function:test"
        )
        aws_request_id: str = "52fdfc07-2182-154f-163f-5f0f9a621d72"

    return LambdaContext()


@pytest.fixture(autouse=True, scope="session")
def set_env_vars():
    # setting env vars
    os.environ["GET_BUS_WAIT_SERVICE_NAME"] = "GET_BUS_SERVICE_NAME"
    os.environ["GET_BUS_WAIT_METRICS_NAMESPACE"] = "GET_BUS_NAMESPACE"
    os.environ["GTSD_BUS_SECRET"] = "bus_secret"
    os.environ["APPSYNC_URL"] = "https://test"
    os.environ["TERMINALS"] = "T1"
    os.environ["AVG_REPLACEMENT_RATE"] = "15"
    os.environ["AVG_CONSUMPTION_RATE"] = "5"
    os.environ["T1"] = "5"
    os.environ["S3_BUCKET_IMPORT_FIXED_CONFIG"] = "gtsd-import-fixed-inputs-dev"
    os.environ["LTA_DATAMALL_ENDPOINT"] = "https://test"
    os.environ["TAXI_API_URL"] = "https://pals.lz.changiairport.com/api"


@pytest.fixture(autouse=True, scope="session")
def s3_client():
    s3_client = boto3.client("s3")
    init_s3(s3_client)

    yield s3_client


@pytest.fixture(autouse=True, scope="session")
def kms_setup():
    kms = boto3.client("kms")
    key = kms.create_key(Description="test data key")
    key_id = key["KeyMetadata"]["KeyId"]
    pytest.kms_key_id = key_id

    kms.generate_data_key(
        KeyId=key_id,
        NumberOfBytes=32,
    )

    yield kms


@pytest.fixture(autouse=True, scope="session")
def ddb_mock():
    dynamodb = boto3.client("dynamodb")

    yield dynamodb


@pytest.fixture(autouse=True, scope="function")
def ddb_client(ddb_mock, kms_setup):
    init_tables(ddb_mock, kms_setup)

    yield ddb_mock

    clear_tables(ddb_mock)


def clear_tables(dynamodb):
    for i in dynamodb.list_tables()["TableNames"]:
        dynamodb.delete_table(TableName=i)
    pytest.dynamodb = None


def init_tables(ddb_client, kms_setup):
    db_model_files = [
        f for f in os.listdir("src/layer_diva/python/models") if re.match(r".*\.py", f)
    ]
    models = [
        importlib.import_module(
            f"src.layer_diva.python.models.{file[:-3]}"
        ).setup_model()
        for file in db_model_files
    ]
    for table, rows in load_file("stubData/init_data.json").items():
        insert(
            ddb_client,
            kms_setup,
            table,
            rows,
            create_encrypted_fields_map(models),
        )


def insert(
    ddb_client,
    kms_setup,
    table,
    rows,
    encrypted_fields: Optional[Dict[str, List[str]]],
):
    for row in rows:
        if (
            encrypted_fields is not None
            and encrypted_fields.get(table, None) is not None
        ):
            encrypt_data(row, kms_setup, encrypted_fields.get(table))
        ddb_client.put_item(TableName=table, Item=row)


def create_encrypted_fields_map(models):
    return reduce(
        lambda acc, model: {**acc, model.Meta.table_name: model.Meta.encrypted_fields},
        models,
        {},
    )


@pytest.fixture(scope="function")
def insert_data_from_file(ddb_client, kms_setup):
    def _insert_data_from_file(
        filename: str, encrpyt_fields: Optional[Dict[str, List[str]]] = None
    ):
        for table, rows in load_file(filename).items():
            insert(ddb_client, kms_setup, table, rows, encrpyt_fields)

    return _insert_data_from_file


@pytest.fixture(scope="function")
def insert_data(ddb_client, kms_setup):
    def _insert_data(
        table: str,
        rows: list[dict],
        encrpyt_fields: Optional[Dict[str, List[str]]] = None,
        encrypt_on_insert: bool = False,
    ):
        rows_to_insert = rows if not encrypt_on_insert else EncryptionClient(kms_setup).encrypt_data(pytest.kms_key_id, rows, encrpyt_fields)
        insert(ddb_client, kms_setup, table, rows_to_insert, encrpyt_fields)

    return _insert_data


@pytest.fixture(autouse=True, scope="session")
def cognito_setup():
    cognito = boto3.client("cognito-idp")
    init_cognito(cognito)
    yield cognito


@pytest.fixture(autouse=True, scope="session")
def ssm_setup(cognito_setup):
    ssm = boto3.client("ssm")
    ssm.put_parameter(
        Name="cognito_user_pool_id",
        Description="",
        Value=pytest.cognito_pool_id,
        Type="String",
    )
    ssm.put_parameter(
        Name="webpush_notification_sns_topic_arn",
        Description="",
        Value=json.dumps({"Parameter": {"Value": "test"}}),
        Type="String",
    )
    yield


@pytest.fixture(autouse=True, scope="function")
def mock_responses():
    # Set up API call mocking
    mock_responses = responses.RequestsMock()
    mock_responses.start()  # activate

    yield mock_responses


def init_s3(s3_client):
    """Init S3 buckets with s3_schema.json
    Args:
        s3_client: boto3 S3 client
    """
    path = Path(__file__).parent / "schemas/s3_schema.json"
    with path.open() as json_file:
        schemas = json.load(json_file)
    for schema in schemas["schemas"]:
        s3_client.create_bucket(
            Bucket=schema["BucketName"],
            CreateBucketConfiguration={"LocationConstraint": "ap-southeast-1"},
        )
        # get file and upload
        data_path = path = (
            str(Path(__file__).parent) + "/schemas/file_data/%s" % schema["BucketName"]
        )
        try:
            files = os.listdir(data_path)

            for file in files:
                if file == ".DS_Store":
                    continue
                file_data = data_path + "/" + file
                if os.path.isdir(file_data):
                    __handle_folder(s3_client, file_data, schema, data_path)
                else:
                    print(file_data)
                    s3_client.put_object(
                        Body=open(file_data).read().encode("utf-8"),
                        Bucket=schema["BucketName"],
                        Key=file,
                    )
        except FileNotFoundError:
            print("No base file for bucket %s" % schema["BucketName"])


def __handle_folder(s3_client, dir_path: str, schema: dict, data_path: str):
    files = os.listdir(dir_path)
    for file in files:
        if file == ".DS_Store":
            continue
        final_path = os.path.join(dir_path, file)
        if os.path.isdir(final_path):
            __handle_folder(s3_client, dir_path, schema)
        else:
            s3_client.put_object(
                Body=open(final_path).read().encode("utf-8"),
                Bucket=schema["BucketName"],
                Key=final_path.replace(data_path + "/", ""),
            )


def encrypt_data(row, kms_setup_fix, encryption_fields):
    """Encrypt individual field
    Args:
        row: DICT, row to be inserted to DB
        kms_setup_fix: function, kms setup function
        encryption_fields: LIST, fields need to be encrypted
    """
    for key, val in row.items():
        val = val.get("S", "")
        if key in encryption_fields and val != "":
            encrypted = kms_setup_fix.encrypt(
                KeyId=pytest.kms_key_id, Plaintext=bytes(val, "utf-8")
            )

            encrypted_value = base64.b64encode(encrypted["CiphertextBlob"]).decode(
                "utf-8"
            )
            val = {"S": encrypted_value}
            row[key] = val


def init_cognito(cognito):
    """Init Cognito
    Args:
        cognito: boto3 client, cognito boto3 client
    """
    path = Path(__file__).parent / "cognito.json"
    with path.open() as json_file:
        cognito_file = json.load(json_file)

    # Create cognito pool and client
    user_pool_id = cognito.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"][
        "Id"
    ]
    pytest.cognito_pool_id = user_pool_id

    client_id = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=str(uuid.uuid4()),
        ReadAttributes=["email"],
    )["UserPoolClient"]["ClientId"]

    # Create user group
    for group_name in cognito_file["group_list"]:
        cognito.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    # Create user
    for user in cognito_file["user_list"]:
        generate_user(cognito, user_pool_id, client_id, user)


def generate_user(cognito, user_pool_id, client_id, user):
    """Create cognito user
    Args:
        cognito: boto3 client, cognito boto3 client
        user_pool_id: STR, user_pool_id
        client_id: STR, client_id
        user: DICT, user to be created
    """
    temp_pw = str(uuid.uuid4())

    result = cognito.admin_create_user(
        UserPoolId=user_pool_id,
        Username=user["username"],
        TemporaryPassword=temp_pw,
        UserAttributes=user["attributes"],
    )
    result = cognito.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=user["username"], GroupName=user["group_name"]
    )

    # print(cognito.list_users_in_group(UserPoolId=user_pool_id, GroupName=user["group_name"]))

    result = cognito.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={"USERNAME": user["username"], "PASSWORD": temp_pw},
    )

    # This sets a new password and logs the user in (creates tokens)
    new_pw = "fnXj$P#wskERr^8qEV"
    result = cognito.respond_to_auth_challenge(
        Session=result["Session"],
        ClientId=client_id,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        ChallengeResponses={"USERNAME": user["username"], "NEW_PASSWORD": new_pw},
    )

    os.environ["ACCESS_TOKEN_" + user["id"]] = result["AuthenticationResult"][
        "AccessToken"
    ]


@pytest.fixture(autouse=True, scope="session")
def sns_client():
    sns_client = boto3.client("sns")
    # sns_client.create_topic(Name=os.environ["SNS_TOPIC"])

    yield sns_client

    for topic in sns_client.list_topics()["Topics"]:
        sns_client.delete_topic(TopicArn=topic["TopicArn"])


def get_default_sns_topic_arn(sns_client):
    return sns_client.list_topics()["Topics"][0]["TopicArn"]


# Not working yet. Would be great to get this to work
@pytest.fixture(scope="function")
def get_sns_messages(sns_client):
    with Mocker() as m:
        url = f"http://localhost:4566/{str(uuid.uuid4())}"
        m.post(url, text="")
        sub = sns_client.subscribe(
            TopicArn=get_default_sns_topic_arn(sns_client),
            Protocol="http",
            Endpoint=url,
            ReturnSubscriptionArn=True,
        )
        yield m
        sns_client.unsubscribe(SubscriptionArn=sub["SubscriptionArn"])


@pytest.fixture(scope="function")
def sqs_client():
    yield boto3.client("sqs")


@pytest.fixture(autouse=True, scope="session")
def secrets_client():
    secrets_client = boto3.client("secretsmanager")
    secrets_client.create_secret(
        Name="bus_secret", SecretString='{"AccountKey":"test"}'
    )

    response = secrets_client.create_secret(
        Name="TAXI_API_USERNAME_AND_PASSWORD",
        SecretString='{"username":"test", "password": "test"}',
    )

    os.environ["TAXI_API_USERNAME_AND_PASSWORD"] = response["ARN"]

    yield secrets_client

    for secret in secrets_client.list_secrets()["SecretList"]:
        secrets_client.delete_secret(
            SecretId=secret["ARN"], ForceDeleteWithoutRecovery=True
        )


@dataclass
class MockFeatureFlags:
    enabled: Dict[str, bool] = field(default_factory=dict)

    def evaluate(self, name: str, default: bool):
        return self.enabled.get(name, default)

    def enable(self, name: str):
        self.enabled[name] = True

    def disable(self, name):
        self.enabled[name] = False


@pytest.fixture(scope="session")
def feature_flag_mock(session_mocker):
    mock = session_mocker.patch(
        "aws_lambda_powertools.utilities.feature_flags.FeatureFlags"
    )
    feature_flag = MockFeatureFlags()
    mock.return_value = feature_flag

    yield feature_flag


class MockAppconfigSessionManager:
    is_error_mode: bool = False
    test_data: dict = {}

    def __init__(self, **kwargs):
        pass

    def get_config(self) -> dict:
        if self.is_error_mode:
            raise ConfigException()
        return self.test_data

    def mock_error(self):
        self.is_error_mode = True

    def mock_data(self, data: dict):
        self.test_data = data

    def mock_config_update(self, data: str):
        data_json: dict = json.loads(data)
        update_value = data_json.pop("values")
        assert data_json == {
            "flags": {
                "isMobileActive": {"name": "Mobile activity switch"},
                "isTVActive": {"name": "TV activity switch"},
                "isTaxiWaitTimesUsingApiForT1": {
                    "name": "Flag for taxi wait time data source"
                },
                "isGTCWaitTimesUsingApiForT1": {
                    "name": "Flag for gtc wait time data source"
                },
            },
            "version": "1",
        }
        self.mock_data(update_value)
        return True

    def reset(self):
        self.is_error_mode = (False,)
        self.test_data = {}


@pytest.fixture(scope="session")
def mock_appconfig_session_manager(session_mocker):
    mock = session_mocker.patch("appconfig_manager.AppconfigSessionManager")
    feature_flag = MockAppconfigSessionManager()
    mock.return_value = feature_flag

    yield feature_flag


@pytest.fixture(scope="function")
def enable_feature_flag(feature_flag_mock):
    feature_flag_mock.enable()
    yield
    feature_flag_mock.disable()


@dataclass
class AppSyncRes:
    data: Optional[dict]
    error: Optional[dict] = None


@pytest.fixture(scope="session")
def evaluate_resolver():
    def _evaluate_resolver(
        code: str, ctx: dict, function: str = "request", profile="sandbox"
    ):
        try:
            from awsume.awsumepy import awsume

            creds = awsume(profile).get_credentials()
            appsync = boto3.client(
                "appsync",
                aws_access_key_id=creds.access_key,
                aws_secret_access_key=creds.secret_key,
                aws_session_token=creds.token,
            )
        except Exception as e:
            print(
                f"Couldn't assume role with awsume to instanciate appsync. Using default creds instead. This error occured: {e}"
            )
            appsync = boto3.client("appsync")

        result = appsync.evaluate_code(
            runtime={"name": "APPSYNC_JS", "runtimeVersion": "1.0.0"},
            code=code,
            context=json.dumps(ctx),
            function=function,
        )
        data = (
            json.loads(result["evaluationResult"])
            if result.get("evaluationResult", None) is not None
            else None
        )
        if result.get("error", None) is None:
            return AppSyncRes(data)
        else:
            return AppSyncRes(data, result["error"])

    return _evaluate_resolver


@pytest.fixture(scope="function")
def mock_mutation_invocations():
    with Mocker() as m:
        m.post(os.environ.get("APPSYNC_URL"), json={"hello": "world"})
        yield m


@pytest.fixture(autouse=True, scope="session")
def appconfig_client():
    appconfig_client = boto3.client(
        "appconfig", region_name=os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1")
    )
    init_appconfig(appconfig_client)

    yield appconfig_client


def init_appconfig(appconfig_client):
    os.environ["APPCONFIG_ENV"] = "gtsd-sandbox"
    os.environ["APPLICATION_NAME"] = "gtsd"
    os.environ["CONFIGURATION_NAME"] = "gtsd-kill-switch-config"
    app_resp = appconfig_client.create_application(
        Name=os.environ["APPLICATION_NAME"],
    )
    pytest.appconfig_appid = app_resp["Id"]

    conf_resp = appconfig_client.create_configuration_profile(
        ApplicationId=app_resp["Id"],
        Name="Feature Flag Conf Profile",
        LocationUri="hosted",
    )
    pytest.appconfig_confprofid = conf_resp["Id"]

    appconfig_client.create_hosted_configuration_version(
        ApplicationId=app_resp["Id"],
        ConfigurationProfileId=conf_resp["Id"],
        Content=json.dumps(
            {
                "flags": {
                    "isMobileActive": {"name": "Mobile activity switch"},
                    "isTVActive": {"name": "TV activity switch"},
                },
                "values": {
                    "isMobileActive": {"enabled": True},
                    "isTVActive": {"enabled": True},
                },
                "version": "1",
            },
            indent=2,
        ).encode("utf-8"),
        ContentType="string",
    )
    os.environ["APPCONFIG_APPID"] = pytest.appconfig_appid
    os.environ["APPCONFIG_CONFPROFILEID"] = pytest.appconfig_confprofid
