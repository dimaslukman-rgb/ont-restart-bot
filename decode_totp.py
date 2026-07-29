"""Helper decode Google Authenticator migration data → TOTP secret.

Cara pakai:
  python decode_totp.py "otpauth-migration://offline?data=..."

Outputnya: secret base32 + info akun.
"""
from __future__ import annotations

import base64
import sys
import urllib.parse


def _read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        b = buf[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if (b & 0x80) == 0:
            break
        shift += 7
    return result, pos


def _read_len_delim(buf: bytes, pos: int) -> tuple[bytes, int]:
    length, pos = _read_varint(buf, pos)
    return buf[pos : pos + length], pos + length


def parse_otp_parameters(buf: bytes) -> dict:
    pos = 0
    out: dict = {"secret_b32": None, "name": None, "issuer": None,
                 "algorithm": "SHA1", "digits": 6, "type": "TOTP"}
    digit_enum = {0: 6, 1: 6, 2: 8}  # DigitCount: UNSPECIFIED/SIX/EIGHT
    while pos < len(buf):
        tag = buf[pos]
        pos += 1
        field = tag >> 3
        wire = tag & 0x7
        if wire == 2:
            val, pos = _read_len_delim(buf, pos)
            if field == 1:
                out["secret_b32"] = base64.b32encode(val).decode().rstrip("=")
            elif field == 2:
                out["name"] = val.decode("utf-8", errors="replace")
            elif field == 3:
                out["issuer"] = val.decode("utf-8", errors="replace")
        elif wire == 0:
            v, pos = _read_varint(buf, pos)
            if field == 4:
                out["algorithm"] = {0: "SHA1", 1: "SHA1", 2: "SHA256",
                                    3: "SHA512", 4: "MD5"}.get(v, f"ALGO_{v}")
            elif field == 5:
                out["digits"] = digit_enum.get(v, v)
            elif field == 7:
                out["type"] = "HOTP" if v == 1 else "TOTP"
        else:
            break
    return out


def decode(uri: str) -> list[dict]:
    """Decode satu atau lebih akun dari `otpauth-migration://...` URI."""
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme != "otpauth-migration":
        raise ValueError("URI harus ber-scheme 'otpauth-migration'")
    qs = urllib.parse.parse_qs(parsed.query)
    if "data" not in qs:
        raise ValueError("Query string tidak punya parameter 'data'")
    raw = base64.b64decode(qs["data"][0])

    pos = 0
    accounts: list[dict] = []
    while pos < len(raw):
        tag = raw[pos]
        pos += 1
        field = tag >> 3
        wire = tag & 0x7
        if wire == 2 and field == 1:
            blob, pos = _read_len_delim(raw, pos)
            accounts.append(parse_otp_parameters(blob))
        else:
            # Lewati field lain (version, batch_size, dll)
            if wire == 2:
                _, pos = _read_len_delim(raw, pos)
            elif wire == 0:
                _, pos = _read_varint(raw, pos)
            else:
                break
    return accounts


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python decode_totp.py \"otpauth-migration://offline?data=...\"")
        return 1

    try:
        accounts = decode(sys.argv[1])
    except Exception as e:  # noqa: BLE001
        print(f"Gagal decode: {e}", file=sys.stderr)
        return 1

    for i, a in enumerate(accounts, 1):
        print(f"\n=== Akun #{i} ===")
        print(f"  Issuer      : {a.get('issuer')}")
        print(f"  Name        : {a.get('name')}")
        print(f"  Algorithm   : {a.get('algorithm')}")
        print(f"  Digits      : {a.get('digits')}")
        print(f"  Type        : {a.get('type')}")
        print(f"  Secret (b32): {a.get('secret_b32')}")
        if a.get("secret_b32"):
            print(f"\n  -> Set di .env: ACSIS_TOTP_SECRET={a['secret_b32']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
