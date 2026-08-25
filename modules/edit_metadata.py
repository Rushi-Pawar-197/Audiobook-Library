# Multiple (chapter-wise) audio files for one book — HARDENED VERSION

import os
import re
import stat
import mimetypes
import shutil
from pathlib import Path
import sys

from mutagen.id3 import ID3, APIC, ID3NoHeaderError, TIT2, TPE1, TALB, TRCK
from mutagen.easyid3 import EasyID3

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import utility as util
from utils import constants as const


def update_metadata(book_dir: str, cover_path: str, artist: str, album: str):
    # ---------- helpers ----------

    def natural_key(s: str):
        return [int(t) if t.isdigit() else t.lower() for t in re.findall(r"\d+|\D+", s)]

    def force_rw(path: Path):
        """Force owner read/write on file."""
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass

    def parse_track_from_title(title: str, default: int) -> int:
        m = re.search(r"\d+", title)
        return int(m.group()) if m else default


    print()
    util.rich_divider(char="=")
    util.log("[bold][dark_turquoise]PHASE 3 : METADATA[/bold][/dark_turquoise]", indent=const.INDENT_PHASE)
    util.rich_divider(char="=")
    

    book_dir = Path(book_dir)
    cover_path = Path(cover_path)

    # ---------- gather MP3 files ----------

    mp3s = sorted(
        [p for p in book_dir.iterdir() if p.suffix.lower() == ".mp3"],
        key=lambda p: natural_key(p.name),
    )

    if not mp3s:
        raise SystemExit("No .mp3 files found.")

    # ---------- cover ----------

    cover_bytes = None
    mime_guess, _ = mimetypes.guess_type(cover_path)
    mime_guess = mime_guess or "image/jpeg"

    if cover_path.exists():
        cover_bytes = cover_path.read_bytes()
    else:
        util.log_warning(" Cover image not found. Continuing without cover.", indent=const.INDENT_FILE_LOG)

    # print(
    #     f"Found {len(mp3s)} MP3 files. "
    #     "Writing ONLY: album, artist, title, track, cover (ID3v2.3)."
    # )

    # ---------- main loop ----------

    for idx, src in enumerate(mp3s, start=1):
        title = src.stem
        track_num = parse_track_from_title(title, idx)

        # Ensure source is readable
        force_rw(src)

        # Create temp file in SAME DIRECTORY (important for atomic replace)
        tmp = src.with_suffix(f".tmp.mp3")

        try:
            # Copy bytes first (no metadata ops yet)
            shutil.copyfile(src, tmp)
            force_rw(tmp)

            # ---------- EasyID3 ----------
            try:
                try:
                    EasyID3(tmp)
                except ID3NoHeaderError:
                    ID3().save(tmp)

                easy = EasyID3(tmp)
                easy["title"] = [title]
                easy["artist"] = [artist]
                easy["album"] = [album]
                easy["tracknumber"] = [str(track_num)]
                easy.save()
            except Exception as e:
                raise RuntimeError(f"EasyID3 failed: {e}")

            # ---------- Raw ID3 ----------
            try:
                try:
                    id3 = ID3(tmp)
                except ID3NoHeaderError:
                    id3 = ID3()
                    id3.save(tmp)
                    id3 = ID3(tmp)

                id3["TIT2"] = TIT2(encoding=3, text=title)
                id3["TPE1"] = TPE1(encoding=3, text=artist)
                id3["TALB"] = TALB(encoding=3, text=album)
                id3["TRCK"] = TRCK(encoding=3, text=str(track_num))

                if cover_bytes:
                    id3.delall("APIC")
                    id3.add(
                        APIC(
                            encoding=3,
                            mime=mime_guess,
                            type=3,
                            desc="Cover",
                            data=cover_bytes,
                        )
                    )

                id3.save(v2_version=3)
            except Exception as e:
                raise RuntimeError(f"ID3 failed: {e}")

            # ---------- atomic replace ----------
            force_rw(src)
            os.replace(tmp, src)
            force_rw(src)

            util.log(f"[cyan1][{idx}/{len(mp3s)}][/cyan1]\n")
            util.log(f"{src.name}\n\n", indent=const.INDENT_FILE)
            util.log(f"title:\t'{title}'", indent=const.INDENT_FILE)
            util.log(f"track:\t{track_num}\n", indent=const.INDENT_FILE)

        except Exception as e:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            util.log_error(f" {src.name}: {e}", indent=const.INDENT_FILE_LOG)

    util.log_ok(" Metadata written.")
