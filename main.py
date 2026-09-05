from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import utility as util


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
    print(f"\nTotal execution time: {util.format_time(total_T)}")
