import sys
from rich.console import Console
from rich.highlighter import NullHighlighter
from pathlib import Path
import subprocess
import shutil
from datetime import datetime
import re

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import constants as const
import config as cfg


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


def setup_logging():

    const.ERR_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    const.COMPLETE_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def start_msg():

    setup_logging()

    title = "Starting Audiobook Standardization Program ..."
    width = 68

    start_log = (
        f"\n\n"
        f"[bold][bright_white]"
        f"+{'-' * width}+\n"
        f"| {title:^{width - 2}} |\n"
        f"+{'-' * width}+"
        f"[/bold][/bright_white]\n"
    )

    log(start_log)


def get_num_files(book_path: str):
    audio_files = sorted(
        file
        for file in book_path.iterdir()
        if (file.is_file() and file.suffix.lower() in const.SUPPORTED_AUDIO_EXTENSIONS)
    )

    if not audio_files:
        log_error(f" No supported audio files found in: " f"{book_path}")
        sys.exit(0)
        return

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


def config_parameters(config_params: list):

    book_dir = Path(config_params[0])
    cover_path = Path(config_params[1])
    artist = config_params[2]
    album = config_params[3]

    audio_files = get_num_files(book_dir)
    const.AUDIO_FILES = audio_files
    est_time_str = get_est_time_str(book_dir)

    n_audio_files = len(audio_files)

    print("\n")
    log("[bright_white]Configuration Parameters :[/bright_white]\n")

    log(f"Book Directory\t: [grey50]{book_dir}[/grey50]")
    log(f"Cover Path\t: [grey50]{cover_path}[/grey50]")
    log(f"Album\t\t: [grey50]{album}[/grey50]")
    log(f"Artist\t\t: [grey50]{artist}[/grey50]\n")
    log(f"No. of Files\t: {n_audio_files}")
    log(f"Est. Max. time\t: [sea_green1]{est_time_str}[/sea_green1]\n")

    book_dir_valid = book_dir and book_dir.is_dir()
    cover_path_valid = cover_path and cover_path.is_file()

    if book_dir_valid and cover_path_valid and artist and album:
        log_ok("Configuration parameters checked")

    else:
        log_warning("Some configuration parameters missing/invalid\n")

        config_miss_flag = input("Continue ? (y/n) : ")
        print()

        if config_miss_flag.lower() == "y":
            log_info("Continuing with missing configuration parameters\n")
        else:
            log_info("Program execution aborted\n")
            sys.exit(0)


def title_card(msg: str, type: str, char: str = "="):

    colour = "bright_white" if type == "phase" else "dark_turquoise"

    print()
    rich_divider(char=char, colour=colour)
    log(
        f"[bold][{colour}]{msg}[/{colour}][/bold]",
        indent=const.INDENT_PHASE,
    )
    rich_divider(char=char, colour=colour)
    print()


def batch_summary(total: int, successful: int, failed: int):

    print()
    rich_divider(char="=")
    log(f" Total      : [bold][white]{total}[/bold][/white]")
    log(f" Successful : [bold][green4]{successful}[/bold][/green4]")
    log(f" Failed     : [bold][red3]{failed}[/bold][/red3]")
    rich_divider(char="=")
    print()


def cleanup(book_path):
    """
    Finalize an audiobook after all processing phases have completed.

    Cleanup is performed only when every log subdirectory is empty.

    If any diagnostic/error log exists:
        - Do nothing.
        - Source files remain intact.
        - Standardized_Audiobook remains intact.
        - Logs remain intact.

    If all log directories are empty:
        1. Remove all source audio files from the book directory.
        2. Remove the logs directory.
        3. Move the contents of Standardized_Audiobook into the book directory.
        4. Remove the now-empty Standardized_Audiobook directory.

    Returns
    -------
    bool
        True  -> cleanup completed.
        False -> cleanup was skipped or failed.
    """

    book_path = Path(book_path)

    if not book_path.is_dir():
        log_error(f"Cleanup failed: directory does not exist: {book_path}")
        return False

    # ========================================================
    # DIRECTORIES
    # ========================================================

    logs_dir = const.ERR_LOGS_DIR
    standardized_dir = Path(const.STANDARDIZED_BOOK_PATH)

    # ========================================================
    # VERIFY LOG DIRECTORY
    # ========================================================

    if not logs_dir.is_dir():
        log_info(f"Cleanup skipped: logs directory not found: {logs_dir}")
        return False

    # --------------------------------------------------------
    # Check every item inside every log subdirectory.
    #
    # Any file means an error/diagnostic exists.
    # We deliberately check recursively so that even a file
    # accidentally placed inside a nested directory prevents
    # destructive cleanup.
    # --------------------------------------------------------

    # ========================================================
    # REMOVE METADATA DIRECTORY
    # ========================================================

    try:
        shutil.rmtree(const.METADATA_PATH)

    except Exception as error:
        log_warning(f"Cleanup failed while removing metadata directory: {error}")

    # =======================================================
    # LOG CLEANUP
    # =======================================================

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

    cleanup_failed = False

    try:
        shutil.rmtree(logs_dir)

    except Exception as error:
        log_warning(f"Cleanup failed while removing logs directory: {error}")
        cleanup_failed = True

    if cleanup_failed:
        return False
    # ========================================================
    # MOVE STANDARDIZED AUDIOBOOK CONTENTS
    # ========================================================

    try:

        for item in standardized_dir.iterdir():

            destination = book_path / item.name

            # This should normally never happen because the source
            # audio files were removed above, but don't overwrite
            # anything accidentally.
            if destination.exists():

                log_warning(
                    f"Cleanup aborted: destination already exists: " f"{destination}"
                )

                return False

            shutil.move(str(item), str(destination))

        # Remove the now-empty directory.
        standardized_dir.rmdir()

    except Exception as error:

        log_warning(f"Cleanup failed while moving standardized audio: {error}")

        return False

    # ========================================================
    # SUCCESS
    # ========================================================

    log_ok("Audiobook cleanup completed.")

    return True
