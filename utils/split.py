#!/usr/bin/env python3

"""Split audiobook files into fixed-length, lossless segments using FFmpeg."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import constants as const


def split_file(input_file: Path, output_dir: Path, part_seconds: int) -> None:
    """Split one audio file with FFmpeg without re-encoding."""
    output_pattern = output_dir / f"{input_file.stem} - part %02d{input_file.suffix}"

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_file),
        "-map",
        "0:a:0",
        "-vn",
        "-c",
        "copy",
        "-f",
        "segment",
        "-segment_time",
        str(part_seconds),
        "-reset_timestamps",
        "1",
        str(output_pattern),
    ]

    result = subprocess.run(command)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed while splitting '{input_file.name}'.")


def verify_outputs(output_dir: Path, input_files: list[Path]) -> None:
    """Verify every input produced at least one valid, non-empty audio segment."""
    for input_file in input_files:
        parts = sorted(
            output_dir.glob(f"{input_file.stem} - part *{input_file.suffix}")
        )
        if not parts:
            raise RuntimeError(
                f"No output segments were produced for '{input_file.name}'."
            )

        for part in parts:
            if not part.is_file() or part.stat().st_size == 0:
                raise RuntimeError(f"Invalid or empty output segment: '{part.name}'.")

            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "a:0",
                    "-show_entries",
                    "stream=index",
                    "-of",
                    "csv=p=0",
                    str(part),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if probe.returncode != 0:
                raise RuntimeError(
                    f"FFprobe could not validate output segment '{part.name}'."
                )


def split_audiobook(input_file: Path, part_length_minutes: int) -> int:
    input_file = Path(input_file)
    part_length_minutes = int(part_length_minutes)

    if not input_file.is_file():
        print(f"[ERROR] File not found: {input_file}")
        return 1

    if input_file.suffix.lower() not in const.SUPPORTED_AUDIO_EXTENSIONS:
        print(f"[ERROR] Unsupported audio file: {input_file}")
        return 1

    if part_length_minutes <= 0:
        print("[ERROR] Part length must be greater than 0 minutes.")
        return 1

    if shutil.which("ffmpeg") is None:
        print("[ERROR] FFmpeg was not found in PATH.")
        return 1

    if shutil.which("ffprobe") is None:
        print("[ERROR] FFprobe was not found in PATH.")
        return 1

    output_dir = input_file.parent
    part_seconds = part_length_minutes * 60

    print(f"[INFO] Input file     : {input_file}")
    print(f"[INFO] Part length    : {part_length_minutes} minutes")
    print()

    try:
        print(f"[INFO] Splitting: {input_file.name}")
        split_file(input_file, output_dir, part_seconds)
        print(f"[OK]   Completed : {input_file.name}")

        print()
        print("[INFO] Verifying split output...")
        verify_outputs(output_dir, [input_file])
        print("[OK]   All output segments verified.")

    except RuntimeError as error:
        print(f"[ERROR] {error}")
        print("[INFO] Original audiobook file was preserved.")
        return 1

    input_file.unlink()

    print()
    print(f"[OK] Split audiobook created: {output_dir}")
    print("[OK] Original audiobook file removed.")
    return 0


# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────


def main():
    if len(sys.argv) != 2:
        print("Usage: python split.py <file>")
        return 1

    return split_audiobook(sys.argv[1], const.DEFAULT_PART_MINUTES)


if __name__ == "__main__":
    raise SystemExit(main())
