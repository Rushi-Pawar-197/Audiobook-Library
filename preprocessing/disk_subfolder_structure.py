from pathlib import Path
import os
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import constants as const
from utils import utility as util

# ============================================================
# Configuration
# ============================================================

BOOK_DIR = Path("/home/rushikesh/Audiobooks/Unprocessed/TAS/")


# ============================================================
# Natural sorting
# ============================================================


def natural_key(path):
    """
    Sort filenames/folder names naturally.

    Examples:

        part 1
        part 2
        part 10

    instead of alphabetical sorting:

        part 1
        part 10
        part 2
    """

    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


# ============================================================
# Find source subdirectories
# ============================================================


def get_subfolders(book_dir):
    """
    Return all immediate subdirectories of BOOK_DIR
    in natural order.

    No naming convention is assumed.

    Examples that all work:

        D01/
        D02/
        D03/

        Disk 1/
        Disk 2/
        Disk 10/

        part 1/
        part 2/
        part 10/

        CD 1/
        CD 2/
        CD 10/

    The program does not care what the folders are called.
    Their natural order determines their processing order.
    """

    folders = [path for path in book_dir.iterdir() if path.is_dir()]

    folders.sort(key=natural_key)

    return folders


# ============================================================
# Find audio files
# ============================================================


def get_audio_files(folder):
    """
    Find supported audio files directly inside a folder
    and return them in natural filename order.
    """

    audio_files = [
        path
        for path in folder.iterdir()
        if (path.is_file() and path.suffix.lower() in const.SUPPORTED_AUDIO_EXTENSIONS)
    ]

    audio_files.sort(key=natural_key)

    return audio_files


# ============================================================
# Create temporary name
# ============================================================


def create_temp_path(path, index):
    """
    Create a temporary filename in the same directory.
    """

    return path.parent / f".preprocess_tmp_{index}{path.suffix.lower()}"


# ============================================================
# Organize audiobook
# ============================================================


def organize_audiobook():

    if not BOOK_DIR.exists():
        raise FileNotFoundError(f"Book directory does not exist:\n{BOOK_DIR}")

    # --------------------------------------------------------
    # Find all source subdirectories
    # --------------------------------------------------------

    folders = get_subfolders(BOOK_DIR)

    if not folders:
        raise RuntimeError(f"No subdirectories found in:\n{BOOK_DIR}")

    util.log_info(" Source folders found:")

    for index, folder in enumerate(folders, start=1):
        print(f"  {index:>2}. {folder.name}")

    print()

    # --------------------------------------------------------
    # Collect all files first
    # --------------------------------------------------------

    files_to_rename = []

    part_number = 1

    for folder_index, folder in enumerate(folders, start=1):

        util.log_info(f" Processing folder {folder_index}: " f"{folder.name}")

        audio_files = get_audio_files(folder)

        if not audio_files:
            util.log_info(" No audio files found.")
            print()
            continue

        for source_file in audio_files:

            destination_file = (
                BOOK_DIR / f"part {part_number}" f"{source_file.suffix.lower()}"
            )

            files_to_rename.append((source_file, destination_file))

            util.log_ok(f"  {source_file.name}" f"  ->  {destination_file.name}")

            part_number += 1

        print()

    if not files_to_rename:
        raise RuntimeError("No supported audio files were found.")

    # --------------------------------------------------------
    # Phase 1:
    #
    # Move every source file to a temporary name first.
    #
    # This prevents filename collisions.
    # --------------------------------------------------------

    temporary_files = []

    try:

        util.log_info(" Preparing files...")

        for index, (source, destination) in enumerate(files_to_rename, start=1):

            temporary = create_temp_path(source, index)

            if temporary.exists():
                raise FileExistsError(
                    f"Temporary file already exists:\n" f"{temporary}"
                )

            os.replace(source, temporary)

            temporary_files.append((temporary, destination, source))

        # ----------------------------------------------------
        # Phase 2:
        #
        # Move temporary files to final names.
        # ----------------------------------------------------

        print()
        util.log_info(" Finalizing names...")

        for temporary, destination, _ in temporary_files:

            if destination.exists():
                raise FileExistsError(f"Destination already exists:\n" f"{destination}")

            os.replace(temporary, destination)

        # ----------------------------------------------------
        # Remove empty source folders
        # ----------------------------------------------------

        print()
        util.log_info(" Removing empty source folders...")

        for folder in folders:

            try:
                folder.rmdir()

            except OSError:
                # Something remains in the directory.
                pass

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        total_parts = len(files_to_rename)

        print()
        util.log_ok(" Audiobook organization complete.")
        util.log_ok(f"\nTotal parts   : {total_parts}")
        util.log_ok(f"Book directory: {BOOK_DIR}")

    except Exception:

        # ----------------------------------------------------
        # Rollback
        # ----------------------------------------------------

        print()
        util.log_error(" Processing failed. " "Attempting rollback...")

        for temporary, _, original_source in reversed(temporary_files):

            if temporary.exists():

                try:
                    os.replace(temporary, original_source)

                except Exception as rollback_error:

                    util.log_error(
                        f" Could not restore "
                        f"{original_source}: "
                        f"{rollback_error}"
                    )

        raise


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    organize_audiobook()
