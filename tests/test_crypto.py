from base64 import urlsafe_b64decode, urlsafe_b64encode

import pytest
from cryptography.fernet import Fernet

from clave import VaultCorrupt
from clave.crypto import decrypt, encrypt


def test_repeated_encryption_uses_distinct_ivs():
    fernet = Fernet(Fernet.generate_key())
    payload = {"v": 1, "value": "fake-秘密"}
    tokens = [encrypt(fernet, payload) for _ in range(8)]

    # A Fernet token starts with a version byte, an 8-byte timestamp, and a 16-byte IV.
    assert len({urlsafe_b64decode(token)[9:25] for token in tokens}) == len(tokens)
    assert all(decrypt(fernet, token) == payload for token in tokens)


@pytest.mark.parametrize("damage", ["truncated", "modified", "wrong-key"])
def test_decryption_rejects_invalid_ciphertext(damage):
    fernet = Fernet(Fernet.generate_key())
    token = encrypt(fernet, {"v": 1, "value": "fake-value"})
    if damage == "truncated":
        token = token[:20]
    elif damage == "modified":
        raw_token = bytearray(urlsafe_b64decode(token))
        raw_token[25] ^= 1
        token = urlsafe_b64encode(raw_token)
    else:
        fernet = Fernet(Fernet.generate_key())

    with pytest.raises(VaultCorrupt, match="authentication or payload validation"):
        decrypt(fernet, token)
