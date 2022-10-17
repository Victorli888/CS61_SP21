"""
Thin wrapper around pyaes that fixes a mode and encryption style, along with a standard format
for encrypted text to be stored in that allows for easily determining the difference between an encrypted and
non-encrypted file.
"""
import base64
import os
import re

import pyaes

HEADER_TEXT = "OKPY ENCRYPTED FILE FOLLOWS\n" + "-" * 100 + "\n"

# used to ensure that the key is correct (helps detect incorrect key usage)
PLAINTEXT_PADDING = b"0" * 16

# matches keys
KEY_PATTERN = r"[a-z2-7]{52}9999"


def generate_key() -> str:
    """
    Generates a random key
    """
    return to_safe_string(os.urandom(32))


def is_valid_key(key: str) -> bool:
    """
    Returns if this is a valid key
    """
    return re.match("^" + KEY_PATTERN + "$", key) is not None


def get_keys(document: str) -> list:
    """
    Gets all valid keys in the given document
    """
    return re.findall(KEY_PATTERN, document)


def encode_and_pad(data: str, to_length: int) -> bytes:
    """
    Pads the given data sequence to the given length with null characters.

    Returns a sequence of bytes.
    """
    encoded = data.encode('utf-8')
    if to_length is None:
        return encoded
    if len(encoded) > to_length:
        raise ValueError("Cannot pad data of length {} to size {}".format(len(encoded), to_length))
    return encoded + b"\0" * (to_length - len(encoded))


def un_pad_and_decode(padded : bytes) -> str:
    """
    Un-pads the given data sequence by stripping trailing null characters and recodes it at utf-8.
    """
    return padded.rstrip(b"\0").decode('utf-8')


def encrypt(data: str, key: str, pad_length: int = None) -> str:
    """
    Encrypt the given data using the given key. Tag the result so that it is clear that this is an encrypted file.
    """
    data_as_bytes = PLAINTEXT_PADDING + encode_and_pad(data, pad_length)

    ciphertext = aes_mode_of_operation(key).encrypt(data_as_bytes)
    encoded_ciphertext = HEADER_TEXT + to_safe_string(ciphertext)
    return encoded_ciphertext


def is_encrypted(encoded_ciphertext: str) -> bool:
    return encoded_ciphertext.startswith(HEADER_TEXT)


def decrypt(encoded_ciphertext: str, key: str) -> str:
    """
    Decrypt the given ciphertext with the given key. The ciphertext must correspond to the format as generated by
        encrypt(data, key)
    """
    if not encoded_ciphertext.startswith(HEADER_TEXT):
        raise ValueError("Invalid ciphertext: does not start with the header")

    ciphertext_no_header = encoded_ciphertext[len(HEADER_TEXT):]
    ciphertext_no_header_bytes = from_safe_string(ciphertext_no_header)
    padded_plaintext = aes_mode_of_operation(key).decrypt(ciphertext_no_header_bytes)
    if not padded_plaintext.startswith(PLAINTEXT_PADDING):
        raise InvalidKeyException
    plaintext = padded_plaintext[len(PLAINTEXT_PADDING):]
    plaintext = un_pad_and_decode(plaintext)
    return plaintext


def to_safe_string(unsafe_bytes: bytes) -> str:
    # use 9 instead of = for padding so that the string looks more homogenous
    return base64.b32encode(unsafe_bytes).decode('ascii').replace("=", "9").lower()


def from_safe_string(safe_string: str) -> bytes:
    return base64.b32decode(safe_string.upper().replace("9", "=").encode('ascii'))


def aes_mode_of_operation(key):
    return pyaes.AESModeOfOperationCTR(from_safe_string(key))


class InvalidKeyException(Exception):
    pass
