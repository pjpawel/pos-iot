from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from io import BytesIO

private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
private_key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
public_key = private_key.public_key()
public_key_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

public_key_str = public_key_pem.decode("utf-8")
private_key_str = private_key_pem.decode("utf-8")

print("Private")
print(private_key_pem.decode("utf-8"))
print("Public:")
print(public_key_pem.decode("utf-8"))

# Private loading

private_key_stream = bytes(private_key_str, "utf-8")

private_key_new = serialization.load_pem_private_key(
    private_key_stream,
    password=None,
)

private_key_pem_new = private_key_new.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
print(private_key_pem_new.decode("utf-8"))

# Public

public_key_stream = bytes(public_key_str, "utf-8")

public_key_new = serialization.load_pem_public_key(public_key_stream)

public_key_pem_new = public_key_new.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
print(public_key_pem_new.decode("utf-8"))
