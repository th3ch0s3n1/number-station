import configparser
import logging
import shutil
import subprocess
import wave
from pathlib import Path
from typing import TypedDict

import cipher  # VernamCipher module

# Configure structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("number_station")

# Base directory relative to this file
BASE_DIR = Path(__file__).resolve().parent

DIGIT_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


class EncryptionResponse(TypedDict):
    raw_text: str
    ciphertext: str
    encrypted_text: str
    key: str | None


class NumberStation:
    """Generates audio voiceover broadcasts for encrypted messages."""

    def __init__(self, config_path: str | Path, stream_config_path: str | Path) -> None:
        self.base_dir = BASE_DIR
        self.voice_dir = self.base_dir / "voice"

        self.config_path = Path(config_path).expanduser().resolve()
        self.stream_config_path = Path(stream_config_path).expanduser().resolve()

        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self) -> None:
        """Loads and validates the station configuration file."""
        if not self.config_path.is_file():
            raise FileNotFoundError(f"Config file does not exist: {self.config_path}")
        self.config.read(self.config_path)

    def resolve_path(self, path_str: str | Path) -> Path:
        """Resolves relative paths against the application base directory."""
        path = Path(path_str).expanduser()
        return path if path.is_absolute() else (self.base_dir / path).resolve()

    def encrypt(self, text: str, key: str | None = None, stream_indices: bool = True) -> EncryptionResponse:
        """Encrypts text using Vernam Cipher with fallback attribute support for EncryptionResult."""
        if not key:
            return {
                "raw_text": text,
                "ciphertext": text,
                "encrypted_text": text,
                "key": key,
            }

        otp = cipher.VernamCipher()
        result = otp.encrypt(text, key)

        # Retrieve ciphertext safely regardless of attribute naming
        ciphertext_val = getattr(
            result, "ciphertext", getattr(result, "ciphertext_digits", str(result))
        )

        # Number stations broadcast 5-digit numeric groups
        if stream_indices:
            if hasattr(result, "chunked_indices"):
                formatted_text = result.chunked_indices(5)
            elif hasattr(result, "chunked_ciphertext"):
                formatted_text = result.chunked_ciphertext(5)
            elif hasattr(cipher.VernamCipher, "chunk"):
                formatted_text = cipher.VernamCipher.chunk(ciphertext_val, 5)
            else:
                formatted_text = ciphertext_val
        else:
            if hasattr(cipher.VernamCipher, "chunk"):
                formatted_text = cipher.VernamCipher.chunk(ciphertext_val, 5)
            else:
                formatted_text = ciphertext_val

        return {
            "raw_text": text,
            "ciphertext": ciphertext_val,
            "encrypted_text": formatted_text,
            "key": getattr(result, "key", key),
        }

    def _get_silence_wav(
        self,
        duration_sec: float = 0.4,
        sample_rate: int = 44100,
        channels: int = 1,
        sampwidth: int = 2,
    ) -> Path:
        """Generates a temporary silent WAV file matching required audio parameters."""
        silence_file = self.voice_dir / "_silence.wav"

        num_frames = int(sample_rate * duration_sec)
        self.voice_dir.mkdir(parents=True, exist_ok=True)

        with wave.open(str(silence_file), "wb") as w:
            w.setnchannels(channels)
            w.setsampwidth(sampwidth)
            w.setframerate(sample_rate)
            w.writeframes(b"\x00" * (num_frames * channels * sampwidth))

        return silence_file

    def get_voice_path(self, character: str) -> Path | None:
        """Maps a character to its corresponding audio file path."""
        char = character.lower()

        if char.isdigit():
            return self.voice_dir / f"{DIGIT_WORDS[int(char)]}.wav"

        # Handle spaces and commas (pauses between 5-character chunks)
        if char in (" ", ",", "."):
            for filename in ("_space.wav", "_pause.wav", "_comma.wav"):
                candidate = self.voice_dir / filename
                if candidate.is_file():
                    return candidate
            # Fallback: Auto-generate a brief silent pause
            return self._get_silence_wav(duration_sec=0.4)

        if char == "\n":
            return self.voice_dir / "intro.wav"

        return None

    def _parse_config_file_list(self, key: str) -> list[Path]:
        """Parses comma-separated file paths from configuration settings."""
        raw_val = self.config.get("streaming", key, fallback="")
        if not raw_val.strip():
            return []

        file_paths: list[Path] = []
        for raw_path in raw_val.split(","):
            cleaned = raw_path.strip()
            if cleaned:
                file_paths.append(self.resolve_path(cleaned))
        return file_paths

    def construct_wav(
        self,
        text: str,
        key: str | None = None,
        agent_id: str = "391",
        repeat_groups: int = 2,
    ) -> Path:
        """Synthesizes a complete number station transmission (Intro -> Preamble -> Message -> Outro)."""
        # 1. Encrypt message and format into 5-digit groups
        enc_res = self.encrypt(text, key, stream_indices=True)
        raw_groups = enc_res["encrypted_text"].split(" ")  # e.g., ['12131', '12118', '00231', '72523']

        payload_groups = [g for g in raw_groups if g != "00000"]
        group_count = len(payload_groups)

        # 2. Format Preamble Header with 0.4s pauses
        # Sequence: [Agent ID] <0.4s> [Agent ID] <0.4s> [Group Count] <0.4s> [Group Count] <0.4s>
        formatted_agent_id = "".join(agent_id.split())
        count_str = f"{group_count:02d}"
        preamble_str = f"{formatted_agent_id} {formatted_agent_id} {count_str} {count_str}"

        # 3. Repeat each 5-digit message group
        repeated_payload = []
        for group in payload_groups:
            repeated_payload.extend([group] * repeat_groups)

        # 4. Format Outro ('00000' EOM repeated)
        eom_str = " ".join(["00000"] * repeat_groups)

        # Combine into complete sequence:
        full_transmission_str = f"{preamble_str}  {' '.join(repeated_payload)}  {eom_str}"

        # Output path setup
        output_dir = (
            self.stream_config_path.parent
            if self.stream_config_path.is_absolute()
            else self.base_dir / "streaming" / self.stream_config_path.parent
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        outfile = output_dir / "message.wav"

        logger.info("Synthesizing Transmission to: %s", outfile)
        logger.info("Agent ID: %s | Unique Groups: %d | Group Repetitions: %dx", agent_id, group_count, repeat_groups)
        logger.info("Transmission Sequence: %s", full_transmission_str)

        infiles: list[Path] = []

        # Step 1: INTRO (Opening chime/melody)
        for file_path in self._parse_config_file_list("prepend"):
            if file_path.is_file():
                infiles.append(file_path)

        # Step 2: PREAMBLE + REPEATED GROUPS + REPEATED EOM
        for char in full_transmission_str:
            vo_path = self.get_voice_path(char)
            if vo_path and vo_path.is_file():
                infiles.append(vo_path)

        # Step 3: OUTRO (Sign-off tone)
        for file_path in self._parse_config_file_list("append"):
            if file_path.is_file():
                infiles.append(file_path)

        # Step 4: Combine WAV audio clips
        self._concatenate_wav_files(infiles, outfile)
        logger.info("Synthesis Complete: %s", outfile)
        return outfile

    @staticmethod
    def _concatenate_wav_files(input_files: list[Path], output_file: Path) -> None:
        """Concatenates multiple WAV files into a single destination file with parameter checks."""
        if not input_files:
            raise ValueError("No valid input WAV files available to combine.")

        audio_frames: list[bytes] = []
        lead_params = None

        for path in input_files:
            with wave.open(str(path), "rb") as w:
                params = w.getparams()
                if lead_params is None:
                    lead_params = params
                elif (params.nchannels, params.sampwidth, params.framerate) != (
                    lead_params.nchannels,
                    lead_params.sampwidth,
                    lead_params.framerate,
                ):
                    logger.warning(
                        "Audio format mismatch in %s: expected %dch/%dbit/%dHz, got %dch/%dbit/%dHz",
                        path.name,
                        lead_params.nchannels,
                        lead_params.sampwidth * 8,
                        lead_params.framerate,
                        params.nchannels,
                        params.sampwidth * 8,
                        params.framerate,
                    )

                audio_frames.append(w.readframes(w.getnframes()))

        if lead_params is None:
            raise RuntimeError("Failed to extract parameters from audio inputs.")

        with wave.open(str(output_file), "wb") as output:
            output.setparams(lead_params)
            for frames in audio_frames:
                output.writeframes(frames)

    def broadcast_message(
        self,
        wav_path: str | Path | None = None,
        frequency: str | float | None = None,
        transmitter_binary: str | None = None,
    ) -> None:
        """Broadcasts a synthesized WAV audio message using an FM transmitter binary (e.g., PiFM)."""
        # 1. Resolve configuration values with fallbacks
        freq = str(
            frequency
            or self.config.get("transmitter", "frequency", fallback="100.0")
        )
        binary_name = (
            transmitter_binary
            or self.config.get("transmitter", "binary", fallback="pifm")
        ).strip()

        # 2. Resolve WAV file target path
        if wav_path:
            target_wav = Path(wav_path).expanduser().resolve()
        else:
            target_wav = self.stream_config_path.parent / "message.wav"

        if not target_wav.is_file():
            raise FileNotFoundError(
                f"Audio file for broadcast does not exist: {target_wav}. "
                f"Run `construct_wav()` first."
            )

        # 3. Locate transmitter binary safely
        bin_path = self.resolve_path(binary_name)
        if not bin_path.is_file():
            # Check system PATH as fallback
            system_bin = shutil.which(binary_name)
            if system_bin:
                bin_path = Path(system_bin)
            else:
                raise FileNotFoundError(
                    f"Transmitter binary '{binary_name}' not found at {bin_path} or in system PATH."
                )

        # 4. Build command vector based on binary signature
        if binary_name.lower() == "pifm":
            cmd = ["sudo", str(bin_path), str(target_wav), freq]
        else:
            cmd = ["sudo", str(bin_path), "-f", freq, str(target_wav)]

        logger.info("Broadcast Begin...")
        logger.info("Executing: %s on %s MHz", bin_path.name, freq)

        # 5. Execute process safely
        try:
            subprocess.run(cmd, check=True)
            logger.info("Broadcast Complete.")
        except subprocess.CalledProcessError as err:
            logger.error("Transmitter failed with exit code %d", err.returncode)
            raise

    def stream_message(self) -> None:
        """Executes Liquidsoap to stream the synthesized audio broadcast."""
        raw_bin = self.config.get("streaming", "liquidsoap_bin", fallback="liquidsoap")
        bin_clean = raw_bin.replace('"', "").strip()
        liquidsoap_bin = shutil.which(Path(bin_clean).expanduser())

        if not liquidsoap_bin:
            raise FileNotFoundError(
                f"Liquidsoap binary not found at '{bin_clean}'. Check configuration."
            )

        stream_dir = self.stream_config_path.parent
        if not stream_dir.exists():
            raise FileNotFoundError(f"Streaming directory does not exist: {stream_dir}")

        if not self.stream_config_path.is_file():
            default_config = self.base_dir / "streaming" / "default" / "main.liq"
            raise FileNotFoundError(
                f"Stream config missing: {self.stream_config_path}. "
                f"Copy default config using: cp {default_config} {stream_dir}/main.liq"
            )

        logger.info("Executing: %s %s", liquidsoap_bin, self.stream_config_path)

        # Subprocess call with modern run() and error checking
        subprocess.run([liquidsoap_bin, str(self.stream_config_path)], check=True)

    @property
    def stream_name(self) -> str:
        """Returns the parent folder name of the streaming configuration."""
        return self.stream_config_path.parent.name


def run_cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Number Station Voice Synthesis CLI")
    parser.add_argument("--text", "-t", required=True, help="Message text to convert")
    parser.add_argument("--key", "-k", default=None, help="Optional Vernam Cipher key")
    parser.add_argument("--config", "-c", default="config.ini", help="Path to config.ini")
    parser.add_argument("--stream-cfg", "-s", default="streaming/default/main.liq", help="Path to Liquidsoap script")
    parser.add_argument("--stream", action="store_true", help="Launch Liquidsoap stream after synthesis")

    # Transmission parameters
    parser.add_argument("--agent-id", "-a", default="391", help="Agent identifier for preamble (default: 391)")
    parser.add_argument("--repeat-groups", "-r", type=int, default=2, help="Number of times to repeat each code group (default: 2)")

    # Broadcast flags
    parser.add_argument("--broadcast", "-b", action="store_true", help="Broadcast message using FM transmitter")
    parser.add_argument("--freq", "-f", type=str, default=None, help="FM broadcast frequency in MHz (e.g. 108.0)")
    parser.add_argument("--transmitter", type=str, default=None, help="Transmitter binary name (e.g. pifm, fm_transmitter)")

    args = parser.parse_args()

    station = NumberStation(config_path=args.config, stream_config_path=args.stream_cfg)
    audio_file = station.construct_wav(
        text=args.text,
        key=args.key,
        agent_id=args.agent_id,
        repeat_groups=args.repeat_groups,
    )

    print(f"Generated: {audio_file}")

    if args.stream:
        station.stream_message()

    if args.broadcast:
        station.broadcast_message(
            wav_path=audio_file,
            frequency=args.freq,
            transmitter_binary=args.transmitter,
        )


if __name__ == "__main__":
    run_cli()
