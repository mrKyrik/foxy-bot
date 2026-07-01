import os

def generate_keys():
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        print("Lütfen önce kriptografi kütüphanesini kurun: pip install cryptography")
        return

    # RSA Anahtar Çifti Oluştur
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    public_key = private_key.public_key()

    # Private Key'i PEM formatında kaydet
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Public Key'i PEM formatında kaydet
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with open("private_key.pem", "wb") as f:
        f.write(pem_private)

    with open("public_key.pem", "wb") as f:
        f.write(pem_public)

    print("✅ Başarılı! 'private_key.pem' ve 'public_key.pem' oluşturuldu.")
    print("DİKKAT: 'private_key.pem' dosyasını ASLA kimseyle paylaşmayın. Sadece AWS Lambda sunucunuzda kalacak.")
    print("'public_key.pem' ise botunuzun içine (core/license.py) eklenecek.")

if __name__ == "__main__":
    generate_keys()
