import argparse
from pathlib import Path
import secrets
import string

# 1. Standard 2-digit mapping (A=01, B=02 ... Z=26)
LETTER_TO_2DIGIT = {char: f"{idx + 1:02d}" for idx, char in enumerate(string.ascii_uppercase)}

# 2. Modulo 10 single-digit mapping for 1:1 5-letter <-> 5-digit alignment
# (A=1, B=2 ... I=9, J=0, K=1 ...)
LETTER_TO_DIGIT = {char: str((idx + 1) % 10) for idx, char in enumerate(string.ascii_uppercase)}


def generate_dual_key(length: int = 100) -> tuple[list[str], list[str], list[str]]:
    """Generates random uppercase letters and their corresponding numeric key formats."""
    letters = [secrets.choice(string.ascii_uppercase) for _ in range(length)]
    
    # 5-letter block maps to 5-digit block (1:1 single digit)
    digits_1digit = [LETTER_TO_DIGIT[c] for c in letters]
    
    # Standard 2-digit pairs (01-26)
    digits_2digit = [LETTER_TO_2DIGIT[c] for c in letters]

    return letters, digits_1digit, digits_2digit


def format_into_groups(items: list[str], group_size: int = 5) -> list[str]:
    """Splits a list into strings of N-item groups."""
    return ["".join(items[i : i + group_size]) for i in range(0, len(items), group_size)]


def export_pad(sheet_id: str, length: int, output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    letters, digits_1d, digits_2d = generate_dual_key(length)

    letter_groups = format_into_groups(letters, group_size=5)
    digit_groups = format_into_groups(digits_1d, group_size=5)

    # 1. Printable Agent Field Pad (Side-by-side Letters and Numbers)
    agent_pad_path = output_dir / f"agent_pad_{sheet_id}.txt"
    with open(agent_pad_path, "w", encoding="utf-8") as f:
        f.write("=============================================================\n")
        f.write("          CONFIDENTIAL - DUAL ONE-TIME PAD FIELD SHEET      \n")
        f.write(f"                        SHEET ID: {sheet_id}                 \n")
        f.write("=============================================================\n\n")
        f.write(" PARALLEL KEY GROUPS (LETTERS & MATCHING 5-DIGIT CODES)      \n")
        f.write("-------------------------------------------------------------\n")

        for i in range(0, len(letter_groups), 4):
            d_row = digit_groups[i : i + 4]

            f.write(f"{'   '.join(d_row)}\n")
            f.write("-------------------------------------------------------------\n")

        f.write("\n           DESTROY THIS SHEET IMMEDIATELY AFTER USE          \n")
        f.write("=============================================================\n")

    # 2. Raw Character Key File (For letter-based station encryption)
    key_char_path = output_dir / f"key_{sheet_id}_chars.txt"
    with open(key_char_path, "w", encoding="utf-8") as f:
        f.write("".join(letters))

    # 3. Raw Numeric Key File (For number-based station encryption)
    key_num_path = output_dir / f"key_{sheet_id}_nums.txt"
    with open(key_num_path, "w", encoding="utf-8") as f:
        f.write(" ".join(digit_groups))

    return agent_pad_path, key_char_path, key_num_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Dual Letter/Number One-Time Pad Generator")
    parser.add_argument("--sheets", "-s", type=int, default=3, help="Number of pad sheets")
    parser.add_argument("--length", "-l", type=int, default=100, help="Total key character length per sheet")
    parser.add_argument("--outdir", "-o", default="pads", help="Output directory")

    args = parser.parse_args()
    out_dir = Path(args.outdir)

    print(f"\n🔐 Generating {args.sheets} Dual-Format OTP sheet(s)...\n")

    for idx in range(1, args.sheets + 1):
        sheet_id = f"{idx:03d}"
        agent_file, char_key, num_key = export_pad(sheet_id=sheet_id, length=args.length, output_dir=out_dir)

        print(f"  [Sheet #{sheet_id}]")
        print(f"  ├── Agent Field Sheet: {agent_file}")
        print(f"  ├── Letter Key File:   {char_key}")
        print(f"  └── Number Key File:   {num_key}\n")

    print("✅ Generation Complete!\n")


if __name__ == "__main__":
    main()
