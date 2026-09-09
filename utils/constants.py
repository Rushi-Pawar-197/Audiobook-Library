from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ============================================================
# Logging constants
# ============================================================

INDENT_FILE = 6
INDENT_FILE_LOG = INDENT_FILE - 1
INDENT_PHASE = 20
LINE_WIDTH = 90

METADATA_PATH = "metadata/"

# ============================================================
# BATCH CONSTANTS
# ============================================================

REQUIRED_FIELDS = {
    "book_id",
    "AUTHOR",
    "BOOK",
    "PREPROCESS",
    "PREPROCESS_TYPE",
    "DSP_PROCESSING",
}

BATCH_DIR = ""

# ============================================================
# PROJECT LOGGING DIRECTORIES
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOGS_DIR = PROJECT_ROOT / "logs"
ERR_LOGS_DIR = ""

LOGS_ANALYSIS = ""
LOGS_CLEANING = ""
LOGS_CONVERSION = ""

COMPLETE_LOGS_DIR = LOGS_DIR / "complete_logs"

# ============================================================
# other_constants
# =============================================================

ERR_FILE_REJECTED = False

STANDARDIZED_BOOK_PATH = ""

# Audio conversion consts


SUPPORTED_AUDIO_EXTENSIONS = [
    # --------------------------------------------------------
    # MPEG / MP3
    # --------------------------------------------------------
    ".mp3",
    ".mp2",
    # --------------------------------------------------------
    # AAC / MPEG-4
    # --------------------------------------------------------
    ".aac",
    ".m4a",
    ".m4b",
    # --------------------------------------------------------
    # Lossless audio
    # --------------------------------------------------------
    ".flac",
    ".wav",
    ".aiff",
    ".aif",
    ".ape",
    ".wv",
    ".tta",
    # --------------------------------------------------------
    # Ogg / Opus
    # --------------------------------------------------------
    ".ogg",
    ".oga",
    ".opus",
    # --------------------------------------------------------
    # Windows Media
    # --------------------------------------------------------
    ".wma",
    # --------------------------------------------------------
    # Dolby / DVD audio
    # --------------------------------------------------------
    ".ac3",
    ".eac3",
    # --------------------------------------------------------
    # AMR / mobile audio
    # --------------------------------------------------------
    ".amr",
    ".3gp",
    ".3gpp",
]
