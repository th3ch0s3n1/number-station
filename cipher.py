import argparse
import secrets
import sys
import unicodedata
from typing import NamedTuple


class EncryptionResult(NamedTuple):
    ciphertext_digits: str
    key: str
    raw_digits: str

    @property
    def ciphertext(self) -> str:
        return self.ciphertext_digits

    def chunked_ciphertext(self, size: int = 5, end_signal: str = "00000") -> str:
        digits = self.ciphertext_digits
        remainder = len(digits) % size
        if remainder != 0:
            digits += "0" * (size - remainder)

        groups = [digits[i : i + size] for i in range(0, len(digits), size)]
        if end_signal:
            groups.append(end_signal)
        return " ".join(groups)

    def chunked_indices(self, size: int = 5, end_signal: str = "00000") -> str:
        return self.chunked_ciphertext(size=size, end_signal=end_signal)


class VernamCipher:
    """Vernam / One-Time Pad Cipher (A=01, B=02 ... Z=26)."""

    @staticmethod
    def chunk(text: str, size: int = 5) -> str:
        cleaned = "".join(text.split())
        return " ".join(cleaned[i : i + size] for i in range(0, len(cleaned), size))

    def encrypt(self, text: str, key: str | None = None) -> EncryptionResult:
        # A=01, B=02, ..., Z=26 (ord('A') - 64 = 1)
        raw_digits = "".join(f"{(ord(c.upper()) - 64):02d}" for c in text if c.isalpha())

        if not key:
            import secrets
            key = "".join(str(secrets.randbelow(10)) for _ in raw_digits)

        used_key = key[: len(raw_digits)]

        ciphertext_digits = ""
        for d, k in zip(raw_digits, used_key):
            enc_digit = (int(d) + int(k)) % 10
            ciphertext_digits += str(enc_digit)

        return EncryptionResult(
            ciphertext_digits=ciphertext_digits,
            key=used_key,
            raw_digits=raw_digits,
        )

    def decrypt(self, ciphertext: str, key: str) -> str:
        clean_cipher = "".join(c for c in ciphertext if c.isdigit())

        # Odstranění koncového signalizačního bloku 00000
        while clean_cipher.endswith("00000"):
            clean_cipher = clean_cipher[:-5]

        # Odstranění výplňových nul (padding)
        if len(clean_cipher) % 5 == 0:
            for pad_len in (2, 4):
                if pad_len < len(clean_cipher):
                    candidate_len = len(clean_cipher) - pad_len
                    if (5 - (candidate_len % 5)) == pad_len and clean_cipher.endswith("0" * pad_len):
                        clean_cipher = clean_cipher[:candidate_len]
                        break

        eval_len = min(len(clean_cipher), len(key))
        eval_len -= eval_len % 2

        target_cipher = clean_cipher[:eval_len]
        target_key = key[:eval_len]

        decrypted_digits = ""
        for c, k in zip(target_cipher, target_key):
            dec_digit = (int(c) - int(k)) % 10
            decrypted_digits += str(dec_digit)

        # Převod dvoumístných čísel zpět na A-Z (01=A, 26=Z)
        chars = []
        for i in range(0, len(decrypted_digits), 2):
            val = int(decrypted_digits[i : i + 2])
            if 1 <= val <= 26:
                chars.append(chr(val + 64))

        return "".join(chars)

    def decrypt_indices(self, indices_text: str, key: str) -> str:
        return self.decrypt(indices_text, key)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vernam",
        description="Traditional Agent One-Time Pad Cipher (Straddling Checkerboard + Modulo 10).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Encrypt
    enc_parser = subparsers.add_parser("encrypt", help="Encrypt a text message")
    enc_parser.add_argument("--text", "-t", required=True, type=str, help="Text to encrypt")
    enc_parser.add_argument("--key", "-k", type=str, default=None, help="Numeric key (optional)")

    # Decrypt
    dec_parser = subparsers.add_parser("decrypt", help="Decrypt a broadcasted digit group")
    dec_parser.add_argument("--text", "-t", required=True, type=str, help="Broadcasted digit stream")
    dec_parser.add_argument("--key", "-k", required=True, type=str, help="Numeric key")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    cipher = VernamCipher()

    try:
        if args.command == "encrypt":
            result = cipher.encrypt(args.text, args.key)

            print(f"Plaintext           : {args.text}")
            print(f"Digit conversion    : {result.raw_digits}")
            print(f"Numeric key (OTP)   : {result.key}")
            print(f"Broadcast (5-digit) : {result.chunked_ciphertext()}")

        elif args.command == "decrypt":
            plaintext = cipher.decrypt(args.text, args.key)
            print(f"Decrypted text      : {plaintext}")

    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()