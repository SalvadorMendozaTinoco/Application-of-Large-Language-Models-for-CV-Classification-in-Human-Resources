from os.path import exists
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
from hashlib import md5
from colorama import Fore, Back
from getpass import getpass

def calculate_md5(file_path):
    """
    Calculate the MD5 hash of a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The MD5 hash of the file.
        False: If there was an error calculating the hash.

    """
    try:
        hash_md5 = md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Error: {e}")
        return False


def generate_key(password: str, salt: bytes) -> bytes:
    """Generate a key from the given password and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())


def decrypt_data(encrypted_data: bytes, password: str) -> bytes:
    """Decrypt the given data with the given password."""
    encrypted_data = base64.b64decode(encrypted_data)
    salt = encrypted_data[:16]
    nonce = encrypted_data[16:28]
    cipher_text = encrypted_data[28:]
    key = generate_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, cipher_text, None)


def _create_env_file(password: str):
    """Create and encrypt the .env file with the given password."""
    env_content = 'rz6uQNgUjff16YSBUKnsAfW/6rcLdv3JrlfVd1Di8z+0Zfe8DtKprcQe4xqiKeqyer3Zqm4U4rh8ODK5p4CxAID51NKaLR1PnNPzeUMiQPQpHkb7xUpw64O+yrTXDtQ6/1QjT/tkX5JPyubGgW6Yyt3Uz9scmkJFwBLp6Gf2uTwfnBGwfpOI7004Wi/vuGLqImTko3Yixln3mYgeiRNtAfUg9mcP7wEA07MHusqpPRk3rTYw/EfVBaq2vfO93pD6Tc0X3eWOV1qCjcQqAdgaKOajGLImPvccvsNLrwPn9ocA/nvlbH0n9HoL9ZGQukgl4UoK/l6POw+xYvoYUTvK0indhq5oEhAeejEUX0x7IM0HNWTRkj5t0uYT/IE3t2ezKFvWIVPuBLPib7AxzFpAIQtwk30bUJatCb2lt5A/xl7NTWow2yKHQVpfsFEnu/qS+ouq/owYFCNGFrm8hdKoU/0UhyP/nw7FNl8qEMSIHPHOhjjLUZAqKyGbRgNvjwghUIu3DdNj59U04QpMbsWlSveK4H3+lvx1bnRowFTbb/xZ43mYS2T1ExB9UCLWLajLtq8ooYqtZIPa3ajWHSl0crI+y43fAa/rif/Mo3UmHtpbnr3PYfJT8y1UHRYGE4Ka7p4XDawEZqekWGQMP1mdygLtXHtuEGcTR20fs4KPf13PKzj8Wa5WPCPMxAcMZlqjERipnwsjuBIBj0L0Htk2SQrf5hi1zkZOc506vcNS2azJ9QH4iGoWkqmBQBkQeYddmgwmgKpvvpJzprONmj0STRYv1SGq/nRXTfvG8hDcr6u6zFrCBc1dS/f/Lj+QIqcW0VOs3+ZpnZpczI6+S5cTk8P0rp/yQTFkF7pEn0xMsPGNN84Oi+lSDXmNP79wzRw46uNKJGj89EGJ+e4pb0GIH3VZyuCtdvbQKMAp/pmfu96iYLOlbrYQrE3b0PO7XGp+jC7kqQGPwyq3AOL6HTOhRIxIaSN14KbCrDswlFlWViY9aqtx9SXpqvY7Vh37xTJlxJrK64x7MqK3LAMsIOrCx8MmrAFLeq6zEf6KcZR5tZ2uTpVTN7Dm3F1xYYrk5WOzY78='
    env_decoded = decrypt_data(env_content, password)
    with open(".env", "wb") as file:
        file.write(env_decoded)

def create_env_file(print_message: bool = False, cont = 0):
    """Create the .env file if it does not exist."""
    try:
        if print_message:
            print(
                "\n-> "
                + Back.GREEN
                + Fore.BLACK
                + "Contraseña:",
                end=""
        )
        password = getpass(" ")
        _create_env_file(password)
        print(Fore.BLUE + "ℹ️ Se ha creado el archivo .env correctamente ℹ️")
    except:
        print(Fore.YELLOW + "⚠️ Contraseña inválida, por favor intente de nuevo ⚠️")
        if cont < 2:
            create_env_file(True, cont + 1)
        else:
            raise Exception("Número máximo de intentos excedido")
