import base64
from unittest import TestCase
import pytest
from encryption_client import EncryptionClient

def test_encryption_and_decryption(kms_setup):
    value = "random"

    encrypted_value = EncryptionClient(kms_setup).encrypt_value(pytest.kms_key_id, value)
    decrypted_value = EncryptionClient(kms_setup).decrypt_value(encrypted_value)

    assert value == decrypted_value

def test_encryption_and_decryption_data(kms_setup):
    data = [{"test": "random"}]
    fields_to_encrypt = ["test"]

    encrypted_data = EncryptionClient(kms_setup).encrypt_data(pytest.kms_key_id, data, fields_to_encrypt)
    decrypted_data = EncryptionClient(kms_setup).decrypt_data(encrypted_data, fields_to_encrypt)
    
    TestCase().assertCountEqual(data, decrypted_data)