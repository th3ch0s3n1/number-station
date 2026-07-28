import sys
from pathlib import Path
from station import NumberStation
from cipher import VernamCipher

def main() -> None:
    # 1. Paths to config files
    config_path = Path("config.ini")
    stream_cfg_path = Path("streaming/default/main.liq")

    # 2. Instantiate Number Station
    station = NumberStation(
        config_path=config_path,
        stream_config_path=stream_cfg_path
    )

    # 3. Message parameters
    message = "ukryt prozrazen"
    secret_key = "8881112832891284743566125945057406042506426423162087255274780209532422543635650881452967694733408198"

    try:
        # 4. Generate the audio broadcast file
        wav_output_path = station.construct_wav(text=message, key=secret_key, agent_id="007", repeat_groups=2)
        print(f"✅ Audio generated successfully at: {wav_output_path}")

        # 5. (Optional) Stream via Liquidsoap
        # station.stream_message()

        # DO NOT BROADCAST INTO PRODUCTION AIRWAVES WITHOUT AUTHORIZATION! 
        # station.broadcast_message()

    except Exception as err:
        print(f"❌ Error during broadcast generation: {err}", file=sys.stderr)

if __name__ == "__main__":
    main()
