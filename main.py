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
    start = time.perf_counter()

    main()

    elapsed = time.perf_counter() - start

    util.log(
        f"\nTotal execution time: [bright_white]{util.format_time(elapsed)}[/bright_white]"
    )
