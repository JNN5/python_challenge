from typing import Optional
from pynamodb.models import Model
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.attributes import UnicodeAttribute
from util_constants import REGION
from util_helper import setup_model as setup_model_helper
from encryption_client import EncryptionClient


class CompanyStartOfWeekIndex(GlobalSecondaryIndex):
    class Meta:
        index_name = "company-start_of_week-index"
        read_capacity_units = 5
        write_capacity_units = 5
        projection = AllProjection()

    company = UnicodeAttribute(hash_key=True)
    start_of_week = UnicodeAttribute(range_key=True)


class Booking(Model):
    class Meta:
        region = REGION
        table_name = "diva-blp-booking"
        encrypted_fields = ["nric_sha"]

    capsule_id = UnicodeAttribute(hash_key=True)
    activity_date = UnicodeAttribute(range_key=True)
    company = UnicodeAttribute()
    start_of_week = UnicodeAttribute()
    location = UnicodeAttribute()
    nric_sha = UnicodeAttribute()
    company_startofweek_index = CompanyStartOfWeekIndex()

    def encrypt(self, kms_key_id: str):
        self.nric_sha = EncryptionClient().encrypt_value(kms_key_id, self.nric_sha)
        return self
    
    def decrypt(self, kms_key_id: Optional[str] = None):
        self.nric_sha = EncryptionClient().decrypt_value(self.nric_sha)
        return self


def setup_model(tablename: Optional[str] = None):
    return setup_model_helper(Booking, tablename)
