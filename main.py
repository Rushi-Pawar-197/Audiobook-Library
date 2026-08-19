from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import constants as const
from utils import utility as util
from modules import audio_dsp_cleaning as dsp
from modules import audio_converter as converter
from modules import edit_metadata as meta

# ========= CONFIG =========

book_dir = Path(const.BOOK_DIR)
album = const.ALBUM
artist = const.ARTIST
cover_path = Path(const.COVER_PATH)

# ==========================

util.start_msg()

util.print_parameters(book_dir)

# sys.exit(0)

dsp.audiobook_cleaning(book_dir)

new_BOOK_DIR = os.path.join(book_dir, "Standardized_Audiobook")

converter.normalize_audiobook(new_BOOK_DIR)

meta.update_metadata(new_BOOK_DIR, cover_path, artist, album)

util.log_ok(" Program execution successful.")