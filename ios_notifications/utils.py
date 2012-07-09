import OpenSSL


def generate_cert_and_pkey(as_string=True, passphrase=None):
    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
    cert = OpenSSL.crypto.X509()
    cert.set_version(3)
    cert.set_serial_number(1)
    cert.get_subject().CN = '127.0.0.1'
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha1')
    if as_string:
        args = [OpenSSL.crypto.FILETYPE_PEM, key]
        if passphrase is not None:
            args += ['DES3', passphrase]
        cert = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        key = OpenSSL.crypto.dump_privatekey(*args)
    return cert, key
