import logging
import os
import boto3
from botocore.config import Config

# LOGGER
log = logging.getLogger()
if log.handlers:
    HANDLER = log.handlers[0]
else:
    HANDLER = logging.StreamHandler()
    log.addHandler(HANDLER)
LOG_FORMAT = '[%(levelname)s] %(asctime)s- %(message)s (File %(pathname)s, Line %(lineno)s)'
HANDLER.setFormatter(logging.Formatter(LOG_FORMAT))
try:
    LOG_LEVEL = os.environ['LOG_LEVEL']
except Exception as e:
    LOG_LEVEL = logging.INFO
log.setLevel(LOG_LEVEL)

config = Config(
    retries={
        'max_attempts': 10,
        'mode': 'standard'
    }
)

COGNITO = boto3.client('cognito-idp', config=config)

class Cognito:
    """Cognito Class:
    This class will perform Cognito-related functions
    """
    def __init__(self, pool_id):
        self.pool_id = pool_id
    
    def get_users(self):
        """
        List all Cognito users in user pool
        Returns:
            users: LIST, all users in the Cognito user pool
        """
        users = []
        
        query_params = {}
        query_params['UserPoolId'] = self.pool_id
        response = COGNITO.list_users(**query_params)
        
        users.extend(self._flatten(user) for user in response['Users'])

        # Paginate
        while 'PaginationToken' in response:
            query_params['PaginationToken'] = response['PaginationToken']
            response = COGNITO.list_users(**query_params)
            users.extend(self._flatten(user) for user in response['Users'])
            
        log.info(f"COGNITO: Found {len(users)} users in user pool.")
                 
        return users
        
    def get_users_in_group(self, user_group):
        """
        List all Cognito users in a user group
        Args:
            pool_id: STR, Cognito user pool id to query
        Returns:
            users: LIST, all users in the Cognito user pool in the specified user group
        """
        users = []
        
        query_params = {}
        query_params['UserPoolId'] = self.pool_id
        query_params['GroupName'] = user_group
        response = COGNITO.list_users_in_group(**query_params)
        
        users.extend(self._flatten(user) for user in response['Users'])

        # Paginate
        while 'NextToken' in response:
            query_params['NextToken'] = response['NextToken']
            response = COGNITO.list_users(**query_params)
            users.extend(self._flatten(user) for user in response['Users'])
        
        log.info(f"COGNITO: Retrieved {len(users)} users in user group {user_group}.")
                 
        return users
    
    def _flatten(self, user):
        flattened_user = {}
        for k, value in user.items():
            if k != 'Attributes':
                flattened_user[k] = value
        
        for name_value_pair in user.get('Attributes', []):
            flattened_user[name_value_pair['Name']] = name_value_pair['Value']
        
        return flattened_user
        
    def create_user(self, email, attributes, user_group):
        """
        Creates user in Cognito and adds it to user group.
        Args:
            email: STR, email address of Cognito user to be created
            attributes: DICT, dictionary containing custom attribute and value
            user_group: STR, user group to add user to (e.g. company_admin, supervisor, etc)
        """
        user_attributes = [
            {
                'Name': 'email_verified',
                'Value': "True"
            },
            {
                'Name': 'email',
                'Value': email
            }
        ]
        for k in attributes:
            user_attributes.append({
                'Name': 'custom:' + k,
                'Value': attributes[k]
            })
            
        COGNITO.admin_create_user(
            UserPoolId=self.pool_id,
            Username=email,
            UserAttributes=user_attributes
        )
        
        COGNITO.admin_add_user_to_group(
            UserPoolId=self.pool_id,
            Username=email,
            GroupName=user_group
        )