########## Date Format ###########
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

########## Regex ###########
NUM_REGEX = r'^\d{1,%s}$'
TEXT_REGEX = r'^([\w\s!@#$%%^&*()+\-=\[\]{};:"\|,.<>\/?\'"]{1,%s})$'
STRICT_TEXT_REGEX = r'^([\w\s()+\-:",.?\'"]{1,%s})$'
DATE_REGEX = r'^(\d{4}-\d{2}-\d{2})$'
NA_REGEX = "NA"
LIST_REGEX = "LIST"
OBJECT_REGEX = "OBJECT"
OBJECT_LIST_REGEX = "OBJECTLIST"

########## DDB Table ############
REGION = "ap-southeast-1"
DDB_BOOKING = "diva-blp-booking"

########## Status ############
SAMPLE_STATUS_ACTIVE = 'Active'
SAMPLE_STATUS_INACTIVE = 'Inactive'

########## Cognito User Groups ##########
COGNITO_ADMIN = 'admin'
COGNITO_SUPERVISOR = 'supervisor'

from zoneinfo import ZoneInfo
LOCAL_TIMEZONE = ZoneInfo("Asia/Singapore")