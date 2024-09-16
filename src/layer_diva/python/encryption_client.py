from typing import Optional
import boto3
import base64

class EncryptionClient:
    kms_client: boto3.client
    def __init__(self, kms_client: Optional[boto3.client] = None):
        self.kms_client = kms_client if kms_client is not None else boto3.client("kms")
    def encrypt_value(self, kms_key_id, value: str):
        encrypted = self.kms_client.encrypt(
            KeyId=kms_key_id,
            Plaintext=bytes(value, "utf-8"),
        )
        return base64.b64encode(encrypted["CiphertextBlob"]).decode("utf-8")


    def encrypt_fields(self, kms_key_id, fields: dict, fields_to_encrypt: list):
        return {
            k: self.encrypt_value(kms_key_id, v) if k in fields_to_encrypt else v
            for k, v in fields.items()
        }


    def encrypt_data(self, kms_key_id, field_list, fields_to_encrypt):
        return [self.encrypt_fields(kms_key_id, f, fields_to_encrypt) for f in field_list]


    def decrypt_value(self, value: str, kms_key_id: Optional[str] = None):
        decrypted = (
            self.kms_client.decrypt(CiphertextBlob=bytes(base64.b64decode(value)))["Plaintext"].decode(
                "utf-8"
            )
            if kms_key_id is None
            else self.kms_client.decrypt(
                CiphertextBlob=bytes(base64.b64decode(value)), KeyId=kms_key_id
            )["Plaintext"].decode("utf-8")
        )
        return decrypted


    def decrypt_fields(self, fields: dict, fields_to_decrypt: list[str], kms_key_id: Optional[str] = None):
        return {
            k: self.decrypt_value(v, kms_key_id) if k in fields_to_decrypt else v for k, v in fields.items()
        }


    def decrypt_data(self, field_list: list[dict], fields_to_decrypt: list[str], kms_key_id: Optional[str] = None):
        return [self.decrypt_fields(f, fields_to_decrypt, kms_key_id) for f in field_list]
