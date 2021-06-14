'''
DOPE Class
'''


__version__ = "2.0.3"
__author__ = "Anubhav Mattoo"

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import HMAC, SHA256, SHA384, SHA512
from Crypto.Random import get_random_bytes
from Crypto.Signature import pss, pkcs1_15
import bchlib
import base64
from typing import Union
from hashlib import blake2b, blake2s
from dill import loads, dumps
from gzip import compress, decompress

# Lookup Tables
AES_MODE_LOOKUP = {
    "GCM": AES.MODE_GCM,
    "SIV": AES.MODE_SIV,
    "CBC": AES.MODE_CBC,
    "OFB": AES.MODE_OFB
}
RATCHET_MODE_LOOKUP = {
    "BLAKE0x0": 0x0,
    "BLAKEx0x": 0x1,
}
HMAC_LOOKUP = {
    "SHA256": SHA256,
    "SHA384": SHA384,
    "SHA512": SHA512
}
HMAC_SIZE_LOOKUP = {
    1024: 128,
    2048: 256,
    3072: 384,
    4096: 512,
    8192: 1024
}
KEY_MODE_LOOKUP = {
    "XOR-BL": 0x0,
    "AND-BL": 0x1,
}
DOPE_HIGHER_LOOKUP = {
    # Higher Byte
    (1024, "GCM", "BLAKE0x0"): b'\x00',
    (1024, "GCM", "BLAKEx0x"): b'\x01',
    (1024, "SIV", "BLAKE0x0"): b'\x04',
    (1024, "SIV", "BLAKEx0x"): b'\x05',
    (1024, "CBC", "BLAKE0x0"): b'\x08',
    (1024, "CBC", "BLAKEx0x"): b'\x09',
    (1024, "OFB", "BLAKE0x0"): b'\x0C',
    (1024, "OFB", "BLAKEx0x"): b'\x0D',

    (2048, "GCM", "BLAKE0x0"): b'\x10',
    (2048, "GCM", "BLAKEx0x"): b'\x11',
    (2048, "SIV", "BLAKE0x0"): b'\x14',
    (2048, "SIV", "BLAKEx0x"): b'\x15',
    (2048, "CBC", "BLAKE0x0"): b'\x18',
    (2048, "CBC", "BLAKEx0x"): b'\x19',
    (2048, "OFB", "BLAKE0x0"): b'\x1C',
    (2048, "OFB", "BLAKEx0x"): b'\x1D',

    (4096, "GCM", "BLAKE0x0"): b'\x20',
    (4096, "GCM", "BLAKEx0x"): b'\x21',
    (4096, "SIV", "BLAKE0x0"): b'\x24',
    (4096, "SIV", "BLAKEx0x"): b'\x25',
    (4096, "CBC", "BLAKE0x0"): b'\x28',
    (4096, "CBC", "BLAKEx0x"): b'\x29',
    (4096, "OFB", "BLAKE0x0"): b'\x2C',
    (4096, "OFB", "BLAKEx0x"): b'\x2D',
}
INV_DOPE_HIGHER_LOOKUP = {
    # Higher Byte
    0x00: (1024, "GCM", "BLAKE0x0"),
    0x01: (1024, "GCM", "BLAKEx0x"),
    0x04: (1024, "SIV", "BLAKE0x0"),
    0x05: (1024, "SIV", "BLAKEx0x"),
    0x08: (1024, "CBC", "BLAKE0x0"),
    0x09: (1024, "CBC", "BLAKEx0x"),
    0x0C: (1024, "OFB", "BLAKE0x0"),
    0x0D: (1024, "OFB", "BLAKEx0x"),

    0x10: (2048, "GCM", "BLAKE0x0"),
    0x11: (2048, "GCM", "BLAKEx0x"),
    0x14: (2048, "SIV", "BLAKE0x0"),
    0x15: (2048, "SIV", "BLAKEx0x"),
    0x18: (2048, "CBC", "BLAKE0x0"),
    0x19: (2048, "CBC", "BLAKEx0x"),
    0x1C: (2048, "OFB", "BLAKE0x0"),
    0x1D: (2048, "OFB", "BLAKEx0x"),

    0x20: (4096, "GCM", "BLAKE0x0"),
    0x21: (4096, "GCM", "BLAKEx0x"),
    0x24: (4096, "SIV", "BLAKE0x0"),
    0x25: (4096, "SIV", "BLAKEx0x"),
    0x28: (4096, "CBC", "BLAKE0x0"),
    0x29: (4096, "CBC", "BLAKEx0x"),
    0x2C: (4096, "OFB", "BLAKE0x0"),
    0x2D: (4096, "OFB", "BLAKEx0x"),
}
DOPE_LOWER_LOOKUP = {
    # Lower Byte
    ("SHA256", "XOR-BL"): b'\x00',
    ("SHA256", "AND-BL"): b'\x01',

    ("SHA384", "XOR-BL"): b'\x10',
    ("SHA384", "AND-BL"): b'\x11',

    ("SHA512", "XOR-BL"): b'\x20',
    ("SHA512", "AND-BL"): b'\x21',
}
INV_DOPE_LOWER_LOOKUP = {
    # Lower Byte
    0x00: ("SHA256", "XOR-BL"),
    0x01: ("SHA256", "AND-BL"),

    0x10: ("SHA384", "XOR-BL"),
    0x11: ("SHA384", "AND-BL"),

    0x20: ("SHA512", "XOR-BL"),
    0x21: ("SHA512", "AND-BL"),
}


def byte_xor(left: bytes, right: bytes) -> bytes:
    '''
    XOR Byte String, 2 input
    '''
    return bytes([a ^ b for a, b in zip(left, right)])


def byte_and(left: bytes, right: bytes) -> bytes:
    '''
    AND Byte String, 2 inputs
    '''
    return bytes([a & b for a, b in zip(left, right)])


class DOPE2(object):
    """
    Double Ratchet Over Parity Exchange(DOPE)
    System Class for DOPE
    Parameters:-
        key: bytes
        bch_poly: int
        ecc_size: int
        aes_mode: str
        ratchet_mode: str
    """
    def __init__(self, key: bytes, bch_poly: int,
                 ecc_size: int, aes_mode: str,
                 nonce: bytes, block_size: int = 512):
        self.__key = key
        self.__bch = bchlib.BCH(bch_poly, ecc_size)
        self.__bch_poly = bch_poly
        self.___fixture = False
        if len(nonce) == 0:
            self.__nonce = get_random_bytes(32)
        elif len(nonce) < 32:
            self.__nonce = blake2s(nonce, digest_size=32).digest()
        elif len(nonce) == 32:
            self.__nonce = nonce
        else:
            raise TypeError(
                f"DOPE does not support nonce of size {len(nonce)}")
        self.__ratchet_count = 0
        if block_size >= 128:
            self.block_size = block_size
        else:
            raise TypeError(
                f"DOPE does not support block size{block_size},"
                + " block must be greater than 128")
        if aes_mode in AES_MODE_LOOKUP:
            self.__aes_mode = aes_mode
            if aes_mode == "SIV":
                self.__aes_size = 512
            else:
                self.__aes_size = 256
        else:
            raise TypeError(f"DOPE does not support {aes_mode} mode")

    def __str__(self):
        DOPE = f'DOPE2_'
        BCH = f'BCH_{self.__bch.t}_{self.__bch.ecc_bytes}_'
        AES = f'AES_{self.__aes_size}_{self.__aes_mode}_'
        BLK = f'BLK_{self.block_size}'
        return DOPE + BCH + AES + BLK

    def __repr__(self):
        return self.__str__()

    def serialize(self):
        khac = blake2b(self.__key, digest_size=32).digest()
        nhac = blake2b(self.__nonce, digest_size=32).digest()
        kvac = blake2b(khac + nhac).digest()
        data = self.block_size.to_bytes(16, 'big')\
            + self.__bch_poly.to_bytes(16, 'big')\
            + self.__bch.t.to_bytes(16, 'big')\
            + self.__nonce
        if self.__aes_mode in ['SIV', 'GCM']:
            nonce = get_random_bytes(16)
            encoder = AES.new(khac, AES_MODE_LOOKUP[self.__aes_mode],
                              nonce=nonce)
            encoder.update(nonce)
            data, tag = encoder.encrypt_and_digest(data)
            data = nonce + data + tag
        else:
            encoder = AES.new(khac, AES_MODE_LOOKUP[self.__aes_mode])
            data = encoder.iv + encoder.encrypt(data)
        data = self.__aes_mode.encode('utf8') + data + kvac
        data = base64.urlsafe_b64encode(data)
        if len(data) >= 80:
            data = b"".join(data[i:i+80] + b"\n"
                            for i in range(0, len(data), 80))
        data = b'-----BEGIN DOPE 2 KEY-----\n'\
            + data + b'-----END DOPE 2 KEY-----'
        return data

    @classmethod
    def marshall(cls, key: Union[str, bytes], password: bytes):
        khac = blake2b(password, digest_size=32).digest()
        data = key.splitlines()[1:-1]
        data = b"".join(data)
        data = base64.urlsafe_b64decode(data)
        aes_mode, niv, data, kvac = data[:3].decode('utf8'),\
            data[3:19], data[19:-64], data[-64:]
        if aes_mode in ['SIV', 'GCM']:
            decoder = AES.new(khac, AES_MODE_LOOKUP[aes_mode], nonce=niv)
            decoder.update(niv)
            data = decoder.decrypt_and_verify(data[:-16], data[-16:])
        else:
            decoder = AES.new(khac, AES_MODE_LOOKUP[aes_mode], iv=niv)
            data = decoder.decrypt(data)
        block_size, bch_poly, ecc_size, nonce =\
            int.from_bytes(data[:16], 'big'),\
            int.from_bytes(data[16:32], 'big'),\
            int.from_bytes(data[32:48], 'big'),\
            data[48:]
        nhac = blake2b(nonce, digest_size=32).digest()
        vkac = blake2b(khac + nhac).digest()
        if vkac != kvac:
            raise ValueError('Key Verification Error')
        return cls(password, bch_poly, ecc_size, aes_mode, nonce, block_size)

    def fixate(self):
        '''
        Fixate at a key and Start Ratchets
        '''
        # Key = BLAKE(BLAKE(Weak Home) XOR BLAKE(Strong Home))
        self.__fixture = True
        hash_pass = blake2b(self.__key).digest()
        hash_nonce = blake2b(self.__nonce).digest()
        if self.__aes_mode == "SIV":
            self.__hkdf = blake2b(byte_xor(hash_pass, hash_nonce))
        else:
            self.__hkdf = blake2b(byte_xor(hash_pass, hash_nonce),
                                  digest_size=32)

    @property
    def nonce(self):
        return self.__nonce

    def ratchet(self, ecc: Union[bytes, bytearray]):
        '''
        Ratchet to Next Key
        '''
        self.__ratchet_count += 1
        if self.__ratchet_count > 2 ** 128:
            raise ValueError('Keys Exhausted')
        key = self.__hkdf.digest()
        self.__hkdf.update(key + bytes(ecc))

    def key(self) -> bytes:
        '''
        Ratchet to Next Home Key
        '''
        if self.__ratchet_count > 2 ** 128:
            raise ValueError('Keys Exhausted')
        key = self.__hkdf.digest()
        return key

    def pack_data(self, data: bytes) -> list:
        '''
        Pack Data to DOPE Standard
        '''
        data_block = []
        for x in range(0, len(data), self.block_size - 4):
            pad_len = 0
            if len(data[x:x+self.block_size - 4]) < self.block_size - 4:
                pad_len = self.block_size\
                    - 4 - len(data[x:x+self.block_size - 4])
            data_x = data[x:x+self.block_size - 4] + get_random_bytes(pad_len)
            pad_len = pad_len.to_bytes(4, 'big')
            data_block.append(pad_len + data_x)
        return data_block

    def encode(self, data: bytes) -> bytes:
        '''
        Encode Data in DOPE Data format
        and Serialise as a byte string
        '''
        if not self.__fixture:
            self.fixate()
        data_block = self.pack_data(data)
        code_string = []
        counter = -1
        for x in data_block:  # x: Data Batch
            counter += 1
            key = self.key()
            ecc = self.__bch.encode(x[4:])
            if self.__aes_mode in ['SIV', 'GCM']:
                nonce = get_random_bytes(16)
                encoder = AES.new(key, AES_MODE_LOOKUP[self.__aes_mode],
                                  nonce=nonce)
                encoder.update(b'DOPE')
                header = b'DOPE' + nonce
                data, tag = encoder.encrypt_and_digest(x[4:])
                packet = {
                    'block': counter,
                    'header': header,
                    'pad_len': x[:4],
                    'data': data,
                    'tag': tag,
                    'ecc': bytes(self.__bch.encode(data))
                }
                code_string.append(dumps(packet))
            else:
                encoder = AES.new(key, AES_MODE_LOOKUP[self.__aes_mode])
                header = b'DOPE' + encoder.iv
                data = encoder.encrypt(x[4:])
                packet = {
                    'block': counter,
                    'header': header,
                    'pad_len': x[:4],
                    'data': data,
                    'ecc': bytes(self.__bch.encode(data))
                }
                code_string.append(dumps(packet))
            self.ratchet(packet['ecc'])
        packets = dumps(code_string)
        self.__fixture = False
        return packets

    def decode(self, data: bytes, start: int = 0, end: int = 0) -> bytes:
        '''
        Decode Data in DOPE Data format
        by marshalling the byte string
        '''
        if not hasattr(self, '__fixture'):
            self.fixate()
        code_string = loads(data)
        data = b''
        if end < start:
            raise ValueError('Inavlid Parameters for \'end\'')
        if end == start == 0:
            end = len(code_string)
        x = 0
        while x < start:
            packet = loads(code_string[x])
            self.ratchet(packet['ecc'])
            x += 1
        for x in range(start, end):
            key = self.key()
            packet = loads(code_string[x])
            if self.__aes_mode in ['SIV', 'GCM']:
                header = packet['header']
                decoder = AES.new(key, AES_MODE_LOOKUP[self.__aes_mode],
                                  nonce=header[4:])
                decoder.update(header[:4])
                p_data = decoder.decrypt_and_verify(packet['data'],
                                                    packet['tag'])
                _, p_data, ecc = self.__bch.decode(p_data, packet['ecc'])
                pad = int.from_bytes(packet['pad_len'], 'big')
                data += p_data[:-pad] if pad != 0 else p_data
            else:
                decoder = AES.new(key, AES_MODE_LOOKUP[self.__aes_mode],
                                  iv=header[4:])
                p_data = decoder.decrypt(packet['data'])
                _, p_data, ecc = self.__bch.decode(p_data, packet['ecc'])
                pad = int.from_bytes(packet['pad_len'], 'big')
                data += p_data[:-pad] if pad != 0 else p_data
            self.ratchet(packet['ecc'])
        self.__fixture = False
        return data
