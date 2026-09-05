import csv
import sys
from rich.console import Console
from rich.highlighter import NullHighlighter
from pathlib import Path
import subprocess
import shutil
from datetime import datetime
import re
import os

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import constants as const
from modules import audio_dsp_cleaning as dsp
from modules import audio_converter as converter
from modules import edit_metadata as meta
from preprocessing import preprocessing as prep


class TeeLogger:

    ANSI_ESCAPE = re.compile(
        r"""
        \x1B
        [@-_]
        [0-?]*
        [ -/]*
        [@-~]
        """,
        re.VERBOSE,
    )

    def __init__(self, terminal, log_file):

        self.terminal = terminal
        self.log_file = log_file

    def write(self, data):

        # Original output → terminal
        self.terminal.write(data)
        self.terminal.flush()

        # ANSI-free output → log file
        clean_data = self.ANSI_ESCAPE.sub("", data)

        self.log_file.write(clean_data)
        self.log_file.flush()

    def flush(self):

        self.terminal.flush()
        self.log_file.flush()


const.COMPLETE_LOGS_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

log_file = open(
    const.COMPLETE_LOGS_DIR / f"run-{timestamp}.log",
    "w",
    encoding="utf-8",
)

sys.stdout = TeeLogger(sys.__stdout__, log_file)
sys.stderr = TeeLogger(sys.__stderr__, log_file)

console = Console(
    file=sys.stdout,
    force_terminal=True,
    color_system="truecolor",
    highlighter=NullHighlighter(),
)


def log(message: str, indent: int = 0):
    console.print(" " * indent + message)


def log_info(message: str, indent: int = 0):
    log(f"[sea_green1][INFO][/sea_green1] {message}", indent)


def log_ok(message: str, indent: int = 0):
    log(f"[bright_green][OK][/bright_green] {message}", indent)


def log_error(message: str, indent: int = 0):
    console.print("\n" + " " * indent + f"[bright_red][ERROR][/bright_red] {message}\n")


def log_warning(message: str, indent: int = 0):
    console.print("\n" + " " * indent + f"[orange1][WARNING][/orange1] {message}\n")


def log_file_error(message: str, log_path):
    """
    Write a processing error to a dedicated log file.
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8") as file:
        file.write(message.rstrip() + "\n")


def setup_logging(book_dir: Path):

    logs_dir = book_dir / "logs"
    const.ERR_LOGS_DIR = logs_dir / "err_logs"

    const.LOGS_ANALYSIS = const.ERR_LOGS_DIR / "phase1_analysis"
    const.LOGS_CLEANING = const.ERR_LOGS_DIR / "phase1_cleaning"
    const.LOGS_CONVERSION = const.ERR_LOGS_DIR / "conversion"

    const.STANDARDIZED_BOOK_PATH = book_dir / "Standardized_Audiobook"

    const.ERR_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def run_ffmpeg(command, stderr_log_path, *, stdout=subprocess.PIPE, text=False):
    """
    Run FFmpeg while redirecting stderr to an operation-specific diagnostic log.

    The log is truncated before each invocation so stale diagnostics from an
    earlier run cannot affect the current status. Empty logs are removed after
    the process finishes; non-empty logs are retained for inspection.

    Returns
    -------
    tuple[subprocess.CompletedProcess, Path | None]
        The completed process and the retained diagnostic-log path, or None
        when FFmpeg produced no diagnostics.
    """

    stderr_log_path = Path(stderr_log_path)
    stderr_log_path.parent.mkdir(parents=True, exist_ok=True)

    with stderr_log_path.open("w", encoding="utf-8") as log_file:
        result = subprocess.run(
            command,
            stdout=stdout,
            stderr=log_file,
            text=text,
        )

    if stderr_log_path.stat().st_size == 0:
        stderr_log_path.unlink()
        return result, None

    return result, stderr_log_path


def rich_divider(char="-", label=None, head_tail=["", ""], colour="dark_turquoise"):
    label_text = f" {label} " if label else ""
    total_fill = (
        const.LINE_WIDTH - len(label_text) - len(head_tail[0]) - len(head_tail[1])
    )
    half = total_fill // 2
    extra = total_fill % 2
    line = (
        f"{head_tail[0]}{char * half}{label_text}{char * (half + extra)}{head_tail[1]}"
    )
    console.print(f"[{colour}]{line}[/{colour}]")


def format_time(elapsed_time):
    """
    Format a duration for display.

    Durations below one second are displayed with
    millisecond precision so that very short audio files
    are not misleadingly shown as 0s.
    """

    if elapsed_time < 1:
        return f"{elapsed_time:.3f}s"

    seconds = int(elapsed_time)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    parts = []

    if hours > 0:
        parts.append(f"{hours}h")

    if minutes > 0 or hours > 0:
        parts.append(f"{minutes}m")

    if seconds > 0 or (hours == 0 and minutes == 0):
        parts.append(f"{seconds}s")

    return " ".join(parts)


def print_filter_chain(filter_chain):
    filter_names = {
        "highpass": "highpass",
        "equalizer": "equalizer",
        "afftdn": "noise reduction",
    }

    log("Filter\t\t:", indent=const.INDENT_FILE)

    if not filter_chain:
        log("No processing required", indent=const.INDENT_PHASE + 6)
        return

    for filter_part in filter_chain.split(","):
        filter_name = filter_part.split("=", 1)[0]

        display_name = filter_names.get(
            filter_name,
            filter_name,
        )

        log(display_name, indent=const.INDENT_PHASE + 6)
    print()


def title_card():

    banner = Path("assets/banner.txt").read_text()

    print(banner)


def get_num_files(book_path: str):
    audio_files = sorted(
        file
        for file in book_path.iterdir()
        if (file.is_file() and file.suffix.lower() in const.SUPPORTED_AUDIO_EXTENSIONS)
    )

    if not audio_files:
        log_error(f" No supported audio files found in: " f"{book_path}")
        return None

    return audio_files


def get_est_time_str(directory):
    """
    Return the combined duration of all audio files in a directory, in seconds.
    """

    total_duration = 0.0
    no_of_files = sum(1 for file in directory.iterdir() if file.is_file())

    for file_path in Path(directory).iterdir():
        if not file_path.is_file():
            continue

        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )

        total_duration += float(result.stdout.strip())

    FFPROBE_TIME_PER_FILE = 0.22
    PREPROCESSING_TIME_PER_FILE = 1
    PROCESSING_RATE = 9.47
    CONVERSION_TIME_PER_AUDIO_MINUTE = 4
    METADATA_TIME_PER_FILE = 3

    ffprobe_time = FFPROBE_TIME_PER_FILE * no_of_files

    preprocessing_time = PREPROCESSING_TIME_PER_FILE * no_of_files

    processing_time = total_duration / PROCESSING_RATE

    conversion_time = total_duration / 60 * CONVERSION_TIME_PER_AUDIO_MINUTE

    metadata_time = METADATA_TIME_PER_FILE * no_of_files

    calculated_est_time = (
        ffprobe_time
        + preprocessing_time
        + processing_time
        + conversion_time
        + metadata_time
    )

    est_time_str = format_time(calculated_est_time)

    return est_time_str


def config_parameters(book_dir, cover_path, artist, album):

    audio_files = get_num_files(book_dir)
    if audio_files == 0 or audio_files is None:
        return False

    n_audio_files = len(audio_files)

    log(f"\nBook Path\t: [grey50]{book_dir}[/grey50]")
    log(f"Cover Path\t: [grey50]{cover_path}[/grey50]")
    log(f"Book\t\t: [grey50]{album}[/grey50]")
    log(f"Author\t\t: [grey50]{artist}[/grey50]\n")
    log(f"No. of Files\t: {n_audio_files}")

    return True


def stage_title_card(msg: str, type: str, char: str = "="):

    colour = "bright_white" if type == "phase" else "dark_turquoise"

    print()
    rich_divider(char=char, colour=colour)
    log(
        f"[bold][{colour}]{msg}[/{colour}][/bold]",
        indent=const.INDENT_PHASE,
    )
    rich_divider(char=char, colour=colour)
    print()


def batch_summary(total: int, good: int, dirty: int):

    print()
    rich_divider(char="=")
    log(f" Total      : [bold][white]{total}[/bold][/white]")
    log(f" Good       : [bold][bright_green]{good}[/bold][/bright_green]")
    log(f" Dirty      : [bold][dark_orange]{dirty}[/bold][/dark_orange]")
    rich_divider(char="=")
    print()


def cleanup(book_path):
    book_path = Path(book_path)

    if not book_path.is_dir():
        log_error(f"Cleanup failed: directory does not exist: {book_path}")
        return False

    # ========================================================
    # RESET METADATA
    # ========================================================

    try:
        if Path(const.METADATA_PATH).is_dir():
            shutil.rmtree(const.METADATA_PATH)

    except Exception as error:
        log_warning(f"Cleanup failed while removing metadata directory: {error}")

    # ========================================================
    # DIRECTORIES
    # ========================================================

    logs_dir = book_path / "logs"
    standardized_dir = Path(const.STANDARDIZED_BOOK_PATH)

    # ========================================================
    # VERIFY LOG DIRECTORY
    # ========================================================

    if not logs_dir.is_dir():
        log_info(f"Cleanup skipped: logs directory not found: {logs_dir}")
        return False

    # ========================================================
    # CHECK LOG FILES
    # ========================================================

    log_files = []

    for path in logs_dir.rglob("*"):
        if path.is_file():
            log_files.append(path)

    if log_files:
        log_warning(
            f"Cleanup skipped: {len(log_files)} log file(s) " f"found in {logs_dir}."
        )
        return False

    # ========================================================
    # VERIFY STANDARDIZED AUDIOBOOK
    # ========================================================

    if not standardized_dir.is_dir():
        log_info("Cleanup aborted: Standardized_Audiobook directory " "was not found.")
        return False

    # ========================================================
    # FIND SOURCE AUDIO FILES
    # ========================================================

    source_files = [
        path
        for path in book_path.iterdir()
        if (path.is_file() and path.suffix.lower() in const.SUPPORTED_AUDIO_EXTENSIONS)
    ]

    # ========================================================
    # REMOVE SOURCE AUDIO
    # ========================================================

    try:
        for source_file in source_files:
            source_file.unlink()

    except Exception as error:
        log_warning(f"Cleanup failed while removing source audio: {error}")
        return False

    # ========================================================
    # REMOVE LOGS
    # ========================================================

    try:
        shutil.rmtree(logs_dir)

    except Exception as error:
        log_warning(f"Cleanup failed while removing logs directory: {error}")
        return False

    # ========================================================
    # MOVE STANDARDIZED AUDIOBOOK CONTENTS
    # ========================================================

    try:
        for item in standardized_dir.iterdir():

            destination = book_path / item.name

            if destination.exists():
                log_warning(
                    f"Cleanup aborted: destination already exists: " f"{destination}"
                )
                return False

            shutil.move(str(item), str(destination))

        standardized_dir.rmdir()

    except Exception as error:
        log_warning(f"Cleanup failed while moving standardized audio: {error}")
        return False

    # ========================================================
    # SUCCESS
    # ========================================================

    log_ok("Audiobook cleanup completed.")

    return True


def load_batch():

    # batch_dir = Path(input("Enter batch directory path : ").strip()).expanduser()
    batch_dir = Path("/home/rushikesh/Audiobooks/Unprocessed/batch/")

    if not batch_dir.is_dir():
        log_error(f"Batch directory not found: {batch_dir}")
        terminate_program()

    const.BATCH_DIR = batch_dir

    metadata_path = batch_dir / "audiobook_metadata.csv"

    if not metadata_path.is_file():
        log_error(f"Batch metadata file not found: {metadata_path}")
        terminate_program()

    try:
        with metadata_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file, skipinitialspace=True)
            books = list(reader)

    except Exception as error:
        log_error(f"Unable to read batch metadata file: {error}")
        terminate_program()

    return {
        "directory": batch_dir,
        "metadata_path": metadata_path,
        "books": books,
    }


def validate_batch(batch):

    batch_dir = batch["directory"]
    books = batch["books"]

    batch_valid = True

    required_fields = const.REQUIRED_FIELDS

    log_info("Checking batch configuration\n")

    # -------------------------------------------------------------------------
    # CSV STRUCTURE
    # -------------------------------------------------------------------------

    if not books:
        log_error("No audiobook entries found in audiobook_metadata.csv")
        terminate_program()

    # -------------------------------------------------------------------------
    # REQUIRED CSV FIELDS
    # -------------------------------------------------------------------------

    csv_fields = set(books[0].keys())

    missing_fields = required_fields - csv_fields

    if missing_fields:

        for field in missing_fields:
            log_error(f"Required CSV field missing: {field}")

        log_error("Batch validation failed. Processing aborted.")
        terminate_program()

    # -------------------------------------------------------------------------
    # BOOK DIRECTORY COUNT
    # -------------------------------------------------------------------------

    book_dirs = [
        path for path in batch_dir.iterdir() if path.is_dir() and path.name != "covers"
    ]

    if len(book_dirs) != len(batch["books"]):
        log_error(
            f"Batch contains {len(batch['books'])} CSV entries but "
            f"{len(book_dirs)} book directories."
        )
        batch_valid = False

    # -------------------------------------------------------------------------
    # BOOK VALIDATION
    # -------------------------------------------------------------------------

    book_ids = []
    book_names = []

    for i, book in enumerate(books, start=1):

        book["book_path"] = None
        book["cover_path"] = None

        book_valid = True

        book_id = book["book_id"].strip()
        author = book["AUTHOR"].strip()
        book_name = book["BOOK"].strip()
        preprocess = book["PREPROCESS"].strip().lower()
        preprocess_type = book["PREPROCESS_TYPE"].strip()

        # -----------------------------------------------------
        # BOOK ID
        # -----------------------------------------------------

        book_id = book["book_id"].strip()

        if not book_id.isdigit() or int(book_id) <= 0:
            log_error(
                f"Book ID '{book_id}' is invalid. "
                "Book ID must be a positive natural number."
            )
            book_valid = False
        else:
            book_id_int = int(book_id)

        if book_id in book_ids:
            log_error(f"Duplicate book ID found: {book_id}")
            book_valid = False
        else:
            book_ids.append(book_id)

        # -----------------------------------------------------
        # AUTHOR / BOOK NAME
        # -----------------------------------------------------

        if not author:

            log_error(f"Author missing for Book {book_id_int}")
            book_valid = False
            batch_valid = False

        if not book_name:

            log_error(f"Book name missing for Book {book_id_int}")
            book_valid = False
            batch_valid = False

        normalized_book_name = book_name.casefold()

        if normalized_book_name in book_names:
            log_error(f"Duplicate BOOK entry found: '{book_name}'.")
            book_valid = False
        else:
            book_names.append(normalized_book_name)

        # -----------------------------------------------------
        # PREPROCESSING
        # -----------------------------------------------------

        if preprocess not in {"y", "n"}:

            log_error(
                f"Invalid PREPROCESS value '{preprocess}' " f"for Book {book_id_int}"
            )

            book_valid = False
            batch_valid = False

        if preprocess == "y":

            if preprocess_type not in {"1", "2"}:

                log_error(
                    f"Invalid PREPROCESS type '{preprocess_type}' "
                    f"for Book {book_id_int}"
                )

                book_valid = False
                batch_valid = False

        # -----------------------------------------------------
        # BOOK DIRECTORY
        # -----------------------------------------------------

        matching_dirs = [
            path for path in book_dirs if path.name.casefold() == book_name.casefold()
        ]

        if not matching_dirs:
            log_error(f"Book {book_id}: no directory matches BOOK " f"'{book_name}'.")
            book_valid = False
        elif len(matching_dirs) > 1:
            log_error(
                f"Book {book_id}: multiple directories match BOOK " f"'{book_name}'."
            )
            book_valid = False
        else:
            book_dir = matching_dirs[0]
            book["book_path"] = book_dir

        # -----------------------------------------------------
        # COVER
        # -----------------------------------------------------

        covers_dir = batch_dir / "covers"

        matching_covers = []

        if covers_dir.is_dir():
            for cover in covers_dir.iterdir():
                if (
                    cover.is_file()
                    and cover.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]
                    and cover.stem.casefold() == book_name.casefold()
                ):
                    matching_covers.append(cover)

        if len(matching_covers) > 1:
            log_error(f"Book {book_id}: multiple covers found for " f"'{book_name}'.")
        elif len(matching_covers) == 0:
            log_warning(f"No matching cover found for Book {book_id}: {book_name}")
        else:
            cover_path = matching_covers[0]
            book["cover_path"] = cover_path

        # -----------------------------------------------------
        # BOOK STATUS
        # -----------------------------------------------------

        if book_valid:
            log_ok(f"Book {book_id} : {book_name}")
        else:
            batch_valid = False

    # -------------------------------------------------------------------------
    # BOOK ID SEQUENCE
    # -------------------------------------------------------------------------

    expected_ids = [str(i) for i in range(1, len(batch["books"]) + 1)]
    actual_ids = sorted(book_ids)

    if actual_ids != expected_ids:
        log_error(
            "Book IDs must form a complete sequential sequence "
            f"from 1 to {len(batch['books'])}."
            f"Expected {expected_ids}, found {actual_ids}"
        )
        batch_valid = False

    # -------------------------------------------------------------------------
    # FINAL VALIDATION STATUS
    # -------------------------------------------------------------------------

    if not batch_valid:
        log_error("Batch validation failed. Processing aborted.")
        terminate_program()

    print()
    log_ok("Batch configuration checked\n")
    rich_divider(char="-")
    print()


def confirm_batch():

    confirmation = input("Proceed with batch processing? (y/n) : ").strip().lower()

    print()

    if confirmation == "y":
        log_info("Proceeding with batch processing\n")
        return True

    log_info("Batch processing aborted\n")
    return False


def process_batch(batch):

    total = len(batch["books"])
    good = 0
    dirty = 0

    books = sorted(batch["books"], key=lambda book: int(book["book_id"]))

    per_book_results = []

    for book in books:
        book_id = book["book_id"].strip()
        book_name = book["BOOK"].strip()

        rich_divider(char="=")
        log(
            f"\n[cyan1][{book_id}/{len(batch['books'])}][/cyan1] [bright_white]Processing Book [bold]{book_id}[/bold][bright_white] : [bold]{book_name}[/bold]\n"
        )
        rich_divider(char="=")

        result = process_single_book(book)
        per_book_results.append(result)

        if result[1]:
            good += 1
        else:
            dirty += 1

    print()
    rich_divider(char="=", colour="bright_white")
    print()
    log_ok(f"Audiobook Batch processing completed")
    print()
    rich_divider(char="=", colour="bright_white")
    batch_status(per_book_results)
    batch_summary(total, good, dirty)


def process_single_book(book):

    book_id = str(book["book_id"].strip())
    author = book["AUTHOR"].strip()
    book_name = book["BOOK"].strip()

    book_dir = book["book_path"]
    cover_path = book["cover_path"]

    preprocess = book["PREPROCESS"].strip().lower()
    preprocess_type = book["PREPROCESS_TYPE"].strip()

    batch_dir = Path(const.BATCH_DIR)

    setup_logging(book_dir)

    valid_audio_files = config_parameters(book_dir, cover_path, author, book_name)

    if not valid_audio_files:
        return [book_name, False]

    prep.preprocessing_pipeline(book_dir, preprocess, preprocess_type)

    dsp.audiobook_cleaning(book_dir)

    new_BOOK_DIR = os.path.join(book_dir, "Standardized_Audiobook")

    converter.normalize_audiobook(new_BOOK_DIR)

    meta.update_metadata(new_BOOK_DIR, cover_path, author, book_name)

    cleanup(book_dir)

    success = not (book_dir / "logs" / "err_logs").exists()

    if success:
        result = [book_name, True]
    else:
        result = [book_name, False]

    return result


def batch_status(per_book_results):

    for idx, (book_name, status) in enumerate(per_book_results, start=1):

        status = (
            "[bright_green]GOOD[/bright_green]"
            if status
            else "[orange1]DIRTY[/orange1]"
        )

        log(
            f"\n[cyan1][{idx}/{len(per_book_results)}][/cyan1]  "
            f"[bold]{book_name}[/bold]\n       Status : {status}"
        )

    print()


def terminate_program():
    log_info("Program execution aborted\n")
    sys.exit(0)
