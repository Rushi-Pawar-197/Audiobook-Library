from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import utility as util

from preprocessing import disk_subfolder_structure as disk
from preprocessing import in_order_rename as order


def preprocessing_pipeline(
    book_dir: Path,
    preprocess: str,
    preprocess_type_num: str,
    operation_kind: str = "Pre-processing",
) -> None:

    if preprocess == "y":
        print()
        util.log_info(f"Started {operation_kind} sequence")

        if preprocess_type_num == "1":
            disk.organize_audiobook(book_dir)

        elif preprocess_type_num == "2":
            order.rename_audiobook(book_dir, operation_kind)

    else:
        print()
        util.log_info(f"Skipped {operation_kind} sequence")

    return
