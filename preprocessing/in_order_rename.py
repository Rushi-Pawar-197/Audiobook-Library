from pathlib import Path
import os
import sys
import re

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import constants as const
from utils import utility as util


def natural_key(path):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


# ============================================================
# Get audio files
# ============================================================


def get_audio_files(directory):

    files = [
        path
        for path in directory.iterdir()
        if (path.is_file() and path.suffix.lower() in const.SUPPORTED_AUDIO_EXTENSIONS)
    ]

    files.sort(key=natural_key)

    return files


# ============================================================
# Rename audiobook files
# ============================================================


def rename_audiobook(directory: Path, type: str, start_index: int = 1) -> None:

    DIRECTORY = directory

    if not DIRECTORY.exists():
        raise FileNotFoundError(f"Directory does not exist:\n{DIRECTORY}")

    files = get_audio_files(DIRECTORY)

    if not files:
        raise RuntimeError(f"No supported audio files found in:\n{DIRECTORY}")

    # --------------------------------------------------------
    # Prepare final names
    # --------------------------------------------------------

    rename_operations = []

    print()

    for index, source_file in enumerate(files, start=start_index):

        new_filename = f"part {index}{source_file.suffix.lower()}"

        destination_file = DIRECTORY / new_filename

        rename_operations.append((source_file, destination_file))

        util.log(
            f"[cyan1][{index}/{len(files)}][/cyan1] {source_file.name}"
            f"  ->  {new_filename}"
        )

    # --------------------------------------------------------
    # Phase 1:
    # Rename everything to temporary names.
    #
    # This prevents collisions such as:
    #
    # file.mp3 -> part 1.mp3
    #
    # when part 1.mp3 already exists.
    # --------------------------------------------------------

    temporary_files = []

    try:

        for index, (source, destination) in enumerate(rename_operations, start=1):

            temporary = DIRECTORY / f".preprocess_tmp_{index}{source.suffix.lower()}"

            if temporary.exists():
                raise FileExistsError(f"Temporary file already exists:\n{temporary}")

            os.replace(source, temporary)

            temporary_files.append((temporary, destination, source))

        # ----------------------------------------------------
        # Phase 2:
        # Rename temporary files to final names.
        # ----------------------------------------------------

        for temporary, destination, _ in temporary_files:

            if destination.exists():
                raise FileExistsError(f"Destination already exists:\n{destination}")

            os.replace(temporary, destination)

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        print()
        util.log_ok(f"{type} sequence complete")
        util.log_ok(f"Total files   : {len(rename_operations)}")
        print()

    except Exception:

        # ----------------------------------------------------
        # Attempt rollback
        # ----------------------------------------------------

        print()
        print("❌ Processing failed. Attempting rollback...")

        for temporary, _, original_source in reversed(temporary_files):

            if temporary.exists():

                try:
                    os.replace(temporary, original_source)
                except Exception as rollback_error:

                    print(
                        f"⚠️ Could not restore "
                        f"{original_source}: "
                        f"{rollback_error}"
                    )

        raise


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    rename_audiobook()
