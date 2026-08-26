from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import utility as util

from preprocessing import disk_subfolder_structure as disk
from preprocessing import in_order_rename as order


def preprocessing_pipeline(book_dir: Path):

    preprocess_flag = input("Perform preprocessing ? (y/n) : ")

    if preprocess_flag.lower() == "y":
        util.log_info("Started preprocessing sequence")

        PP_type = input(
            "\nSelect preprocessing type : \n\n1. Disk subfolder structure\n2. In-order renaming\n3. Cancel\n\nEnter choice (1/2/3) : "
        )

        if PP_type == "1":
            disk.organize_audiobook(book_dir)
        elif PP_type == "2":
            order.rename_audiobook(book_dir)
        else:
            util.log_info("Preprocessing sequence cancelled.")

    else:
        util.log_info("Preprocessing sequence skipped")
        return

    return
