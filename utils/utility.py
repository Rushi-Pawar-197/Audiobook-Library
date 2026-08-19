import sys
from rich.console import Console
from rich.highlighter import NullHighlighter
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import constants as const

console = Console(
    file=sys.stdout,
    force_terminal=True,
    color_system="truecolor",
    highlighter=NullHighlighter(),
)

def log(message):
    console.print(message)


def log_info(message):
    console.print(f"[bright_white][INFO][/bright_white] {message}")


def log_ok(message):
    console.print(f"[bright_green][OK][/bright_green] {message}")


def log_error(message):
    console.print(f"[bright_red][ERROR][/bright_red] {message}")


def rich_divider(char="-", label=None, head_tail=["", ""]):
    label_text = f" {label} " if label else ""
    total_fill = (
        const.line_width - len(label_text) - len(head_tail[0]) - len(head_tail[1])
    )
    half = total_fill // 2
    extra = total_fill % 2
    line = (
        f"{head_tail[0]}{char * half}{label_text}{char * (half + extra)}{head_tail[1]}"
    )
    console.print(line)


def format_time(elapsed_time):
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

    print(" " * 6, "Filter\t\t:")

    if not filter_chain:
        print(" " * 26, "No processing required")
        return

    for filter_part in filter_chain.split(","):
        filter_name = filter_part.split("=", 1)[0]

        display_name = filter_names.get(
            filter_name,
            filter_name,
        )

        print(" " * 26, display_name)

def start_msg():

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
        log_info(f" No supported audio files found in: " f"{book_path}")
        return

    return audio_files

def get_est_time_str(directory):
    """
    Return the combined duration of all audio files in a directory, in seconds.
    """

    total_duration = 0.0

    for file_path in Path(directory).iterdir():
        if not file_path.is_file():
            continue

        command = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )

        total_duration += float(result.stdout.strip())


    calculated_est_time = int((104/2589) * total_duration) + total_duration/135 + 5 * len(const.AUDIO_FILES)

    est_time_str = format_time(calculated_est_time)
        
    return est_time_str


def print_parameters(book_path: str):

    audio_files = get_num_files(book_path)
    const.AUDIO_FILES = audio_files
    est_time_str = get_est_time_str(book_path)

    log(f"Directory\t: [orange3]{book_path}[/orange3]")
    print(f"No. of Files\t: {len(audio_files)}")
    log(f"Estimated time\t: [sea_green1]{est_time_str}[/sea_green1]")
