# One Time Pad & Numbers Station Generator

Pythonová knihovna a nástroj pro šifrování a dešifrování zpráv pomocí **Vernamovy šifry** (One-Time Pad / OTP) s formátováním výstupu pro **číselné stanice** (krátkovlnné audio vysílání).

---

## ⚠️ Důležité upozornění

Tento projekt je vytvořen **pouze pro studijní účely**. 

> **Vysílání na rádiových frekvencích bez licence a oprávnění je nelegální.** 
> Autor nenese žádnou odpovědnost za zneužití kódu nebo porušení platných zákonů.


## 🚀 Hlavní funkce

* **Mapování A1Z26:** Převod abecedy $A=01 \dots Z=26$ do dvoumístných číselných kódů.
* **Šifrování Modulo 10:** Bezpečná operace Vernamovy šifry nad číselným proudem ($0–9$).
* **Formátování pro vysílání:** Automatické rozdělení ciferného proudu do 5místných skupin (např. `08912 84241 ...`).
* **Signalizace EOM:** Připojení koncového bloku `00000` (End of Message) pro rádiové relace.
* **Inteligentní dešifrování:** Automatické čištění výplňových nul (padding) a signalizačních EOM bloků při dešifrování.

---

## 📦 Instalace a požadavky

Knihovna používá pouze standardní knihovnu Pythonu 3.10+ (bez externích závislostí).

```bash
git clone https://github.com/th3ch0s3n1/numbers-station.git
cd numbers-station

```

---

## 💻 Použití

### 1. Šifrování textu do číslicového vysílání

```python
from cipher import VernamCipher

cipher = VernamCipher()

# Zpráva a klíč (28 číslic pro 14 písmen)
key = "8881112832891284743566125945"
text = "ukryt prozrazen"

# Šifrování
result = cipher.encrypt(text, key)

# Formátovaný výstup pro vysílání
broadcast_text = result.chunked_indices()

print(f"Původní text : {text}")
print(f"Číselný proud : {broadcast_text}")
# Výstup: 08912 84241 94299 89942 66375 35800 00000

```

### 2. Dešifrování zachyceného vysílání

```python
from cipher import VernamCipher

cipher = VernamCipher()

broadcast_text = "08912 84241 94299 89942 66375 35800 00000"
key = "8881112832891284743566125945"

# Dešifrování přímo z 5místných skupin
plaintext = cipher.decrypt_indices(broadcast_text, key)

print(f"Dešifrovaný text: {plaintext}")
# Výstup: UKRYTPROZRAZEN

```

---

## 📐 Jak to funguje?

### 1. Převod textu na číselné dvojice (A1Z26)

Každé písmeno zprávy je převedeno na dvoumístný kód od `01` do `26`:

| Písmeno | Kód | Písmeno | Kód |
| --- | --- | --- | --- |
| **A** | `01` | **N** | `14` |
| **B** | `02` | **O** | `15` |
| ... | ... | ... | ... |
| **K** | `11` | **U** | `21` |
| **M** | `13` | **Z** | `26` |

Slovo **`UKRYT`** se převede na:

`21 11 18 25 20` $\rightarrow$ číselný řetězec `2111182520`.

### 2. Šifrování / Dešifrování (Modulo 10)

Šifrování i dešifrování probíhá **po jednotlivých číslicích** podle vzorců:

* **Šifrování:**
$$C_i = (P_i + K_i) \pmod{10}$$


* **Dešifrování:**
$$P_i = (C_i - K_i) \pmod{10}$$



*(kde $P$ je číslice zprávy, $K$ číslice klíče a $C$ číslice šifrového textu).*

### 3. Zpracování skupin a EOM

* Výsledný proud číslic je rozdělen do skupin po 5 číslicích.
* Pokud poslední skupina není plná, doplní se unencrypted výplňovými nulami (`00`).
* Na konec relace se připojí signalizační blok **`00000`** pro označení konce vysílání.

---

## 🛠️ Architektura projektu

```text
.
├── cipher.py          # Hlavní třída VernamCipher a EncryptionResult
├── station.py         # (Volitelné) Generování audia / propojení s Liquidsoap
└── README.md          # Dokumentace projektu

```

---

## ⚠️ Bezpečnostní upozornění (One-Time Pad)

Aby byla Vernamova šifra **matematicky neprolomitelná**, musí být dodržena tato pravidla:

1. Klíč musí být **zcela náhodný** (používejte kryptograficky bezpečné generátory jako `secrets`).
2. Klíč musí být **stejně dlouhý nebo delší** než samotná zpráva.
3. Klíč nesmí být **nikdy použit znovu** (One-Time Pad). Po odvysílání zprávy klíč skartujte.

```

```
