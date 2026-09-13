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
# Audio processing constants
# ============================================================

NOISE_FLOOR_SILENCE_THRESHOLD_DBFS = -90.0
# Conservative audiobook playback target.  This is intentionally a
# fixed library target rather than a per-book average so that different
# audiobooks in the library have a consistent listening level.
AUDIOBOOK_TARGET_LUFS = -23.0

# Prevent an unusually quiet recording from receiving an excessive gain
# boost, even when its measured true peak would technically allow it.
MAX_LOUDNESS_BOOST_DB = 8.0

# Leave 1 dB of true-peak headroom after loudness gain.
TRUE_PEAK_LIMIT_DB = -1.0

# Maximum valid duration allowed in DSP analysis (in seconds)
VALID_MAX_DURATION = 7200

SKIP_DSP_OF_THIS_FILE = False

SKIP_DSP_FILES = []


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


# ============================================================
# TIME ANALYSIS CONSTANTS
# ============================================================

FFMPEG_TIME = 0
PYTHON_TIME = 0
PYTHON_DSP_TIME = 0

Entire_analyze_audio = 0
calculate_loudness = 0
calculate_loudness_list = []
analyze_audio_list = []
