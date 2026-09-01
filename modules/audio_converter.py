from pathlib import Path
import subprocess
import os
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import constants as const
from utils import utility as util
from preprocessing import in_order_rename as rename


def normalize_audio_file(input_extension: str, book_path: str):
    """
    Convert all files with the given input extension to the output format
    specified in constants.py.

    Example:
        normalize_audio(".m4a")
        normalize_audio(".flac")
    """

    book_path = Path(book_path)

    if book_path.is_file():
        files = [book_path]
        book_dir = book_path.parent
    elif book_path.is_dir():
        book_dir = book_path

        files = sorted(
            [
                path
                for path in book_dir.iterdir()
                if (path.is_file() and path.suffix.lower() == input_extension.lower())
            ],
            key=lambda path: path.name.lower(),
        )
    else:
        raise FileNotFoundError(book_path)

    # book_dir = book_path
    BITRATE = "128k"
    OUTPUT_EXTENSION = ".mp3"
    OUTPUT_CODEC = "libmp3lame"

    if not files:
        return

    for i, src in enumerate(files, start=1):

        tmp = book_dir / f"{src.stem}.tmp{OUTPUT_EXTENSION}"
        dst = book_dir / f"{src.stem}{OUTPUT_EXTENSION}"

        if dst.exists():
            util.log_info(
                f" {dst.name} already exists. " f"Removing source {src.name}."
            )
            src.unlink()
            continue

        if tmp.exists():
            tmp.unlink()

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(src),
            "-codec:a",
            OUTPUT_CODEC,
            "-b:a",
            BITRATE,
            str(tmp),
        ]

        stderr_log = os.path.join(const.LOGS_CONVERSION / f"{src.name}.stderr")

        try:
            result, diagnostic_log = util.run_ffmpeg(
                cmd,
                stderr_log,
            )

            if result.returncode != 0:
                if tmp.exists():
                    tmp.unlink()
                util.log_error(f" FFmpeg conversion failed for {src.name}.")
                if diagnostic_log is not None:
                    util.log(f" See {diagnostic_log}")
                continue

            if not tmp.exists():
                util.log_error(f" FFmpeg conversion produced no output for {src.name}.")
                if diagnostic_log is not None:
                    util.log(f" See {diagnostic_log}")
                continue

            tmp.replace(dst)
            src.unlink()

            util.log(f"[cyan1] [{i}/{len(files)}][/cyan1] {src.name} -> {dst.name}")

            if diagnostic_log is not None:
                util.log_warning(
                    f"FFmpeg reported decoding issues while converting {src.name}. "
                    f"See {diagnostic_log}.\n"
                )

        except Exception as e:
            if tmp.exists():
                tmp.unlink()
            util.log_error(f" {src.name}: {e}")

    print()
    util.log_ok(f" Audio conversion complete\n")


def normalize_audiobook(book_dir: str):

    # ---------- Convert supported audio formats to the standard format (.mp3) ----------

    util.title_card("PHASE 2 : AUDIO CONVERSION", type="phase", char="=")

    for extension in const.SUPPORTED_AUDIO_EXTENSIONS:

        # Skip the .mp3 format itself
        if extension == ".mp3":
            continue

        normalize_audio_file(extension, book_dir)

    if const.ERR_FILE_REJECTED:

        util.log_info("Audio files renaming required")
        print()
        util.log_ok("Initiated renaming sequence\n")
        rename.rename_audiobook(const.STANDARDIZED_BOOK_PATH)
