from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config as cfg
from utils import constants as const
from utils import utility as util
from modules import audio_dsp_cleaning as dsp
from modules import audio_converter as converter
from modules import edit_metadata as meta
from preprocessing import preprocessing as prep

import time

start_T = time.time()

# ========= CONFIG =========

config_parameters = [cfg.BOOK_DIR, cfg.COVER_PATH, cfg.ARTIST, cfg.ALBUM]

book_dir = Path(cfg.BOOK_DIR)
album = cfg.ALBUM
artist = cfg.ARTIST
cover_path = Path(cfg.COVER_PATH)

# ==========================

util.start_msg()

prep.preprocessing_pipeline(book_dir)

util.config_parameters(config_parameters)

dsp.audiobook_cleaning(book_dir)

new_BOOK_DIR = os.path.join(book_dir, "Standardized_Audiobook")

converter.normalize_audiobook(new_BOOK_DIR)

meta.update_metadata(new_BOOK_DIR, cover_path, artist, album)

final_cleanup_executed = util.cleanup(cfg.BOOK_DIR)

print()
util.log_ok("Program execution successful.")


end_T = time.time()
total_T = end_T - start_T
print(f"\nTotal execution time: {util.format_time(total_T)}")
