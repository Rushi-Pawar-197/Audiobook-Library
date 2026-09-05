from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import utility as util

from preprocessing import disk_subfolder_structure as disk
from preprocessing import in_order_rename as order


def preprocessing_pipeline(book_dir: Path, preprocess: str, preprocess_type: str):

    if preprocess == "y":
        print()
        util.log_info("Started preprocessing sequence")

        if preprocess_type == "1":
            disk.organize_audiobook(book_dir)

        elif preprocess_type == "2":
            order.rename_audiobook(book_dir)

    else:
        util.log_info("Preprocessing sequence skipped")

    return
