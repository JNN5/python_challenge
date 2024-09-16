import boto3
import json
from aws_lambda_powertools import Logger, Tracer

log = Logger()
tracer = Tracer()

class ConfigException(Exception):
    pass

class AppconfigSessionManager:
    def __init__(self, app_id, app_env_id, config_profile_id):
        self.client = boto3.client("appconfigdata")
        self.session = self.client.start_configuration_session(
            ApplicationIdentifier=app_id,
            EnvironmentIdentifier=app_env_id,
            ConfigurationProfileIdentifier=config_profile_id,
        )
        self.config_token = self.session.get("InitialConfigurationToken")

    def get_config(self) -> dict:
        if not self.config_token:
            log.error("Missing config token")
            raise ConfigException("Could not retrieve configurations")

        get_latest_configuration_response: dict = self.client.get_latest_configuration(
            ConfigurationToken=self.config_token
        )
        log.info(
            {"get_latest_configuration_response": get_latest_configuration_response}
        )
        self.config_token = get_latest_configuration_response.get(
            "NextPollConfigurationToken"
        )
        if not get_latest_configuration_response.get("Configuration"):
            log.error("Could not get configuration from session")
            raise ConfigException("Could not retrieve configurations")
        
        raw_config = get_latest_configuration_response.get("Configuration").read().decode("utf-8")
        if not raw_config and self.latest_config:
            log.info("Current config is latest")
            return self.latest_config

        log.info({"raw_config": raw_config})
        config = json.loads(raw_config)
        self.latest_config = config

        return config
