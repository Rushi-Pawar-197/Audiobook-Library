from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import utility as util
from utils import constants as const


def main():

    util.title_card()

    batch = util.load_batch()

    util.validate_batch(batch)

    if not util.confirm_batch():
        util.terminate_program()

    util.process_batch(batch)

    util.log_ok("Program execution successful")


if __name__ == "__main__":
    start_T = time.time()

    main()

    end_T = time.time()
    total_T = end_T - start_T

    const.PYTHON_TIME = total_T - const.FFMPEG_TIME

    print(f"\nTotal execution time: {util.format_time(total_T)}")

    print(f"\nFFMPEG time : {util.format_time(const.FFMPEG_TIME)}")
    print(f"\nTotal Python time: {util.format_time(const.PYTHON_TIME)}")
    print(
        f"\nDSP module time (within python): {util.format_time(const.PYTHON_DSP_TIME)}"
    )
    print("\n\n")
    print(f"\n calculate_loudness : {util.format_time(const.calculate_loudness)}")
    print(f"\n Entire_analyze_audio : {util.format_time(const.Entire_analyze_audio)}")
    print(f"\n calculate_loudness_list : {const.calculate_loudness_list}")
