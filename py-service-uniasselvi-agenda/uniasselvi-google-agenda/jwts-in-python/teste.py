import os
# first import the module
from cryptography.hazmat.primitives import serialization
import jwt

payload_data = {
  "iat": 1662984587,
  "exp": 1663589387,
  "roles": [
    "ROLE_USER"
  ],
  "username": "08552356597",
  "simulate": "false",
  "specializations": [
    "3524024",
    "3538867"
  ]
}

header = {
  "typ": "JWT",
  "alg": "RS256"
}

# read and load the key
private_key_path = os.getenv("JWT_PRIVATE_KEY_PATH", ".ssh/id_rsa")
private_key_passphrase = os.getenv("JWT_PRIVATE_KEY_PASSPHRASE", "")
private_key = open(private_key_path, 'r').read()

password = private_key_passphrase.encode() if private_key_passphrase else None
key = serialization.load_ssh_private_key(private_key.encode(), password=password)

# my_secret = 'my_super_secret'

token = jwt.encode(
    payload=payload_data,
    key=key,
    algorithm='RS256'
)

print(token)