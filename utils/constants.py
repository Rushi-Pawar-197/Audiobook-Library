# constants for Ausiobook formatting module


BOOK_DIR = "/home/rushikesh/Audiobooks/Unprocessed/time test/test_book/"

COVER_PATH = "/home/rushikesh/Audiobooks/covers/Foundation/F7.png"

ARTIST = "Isaac Asimov"

ALBUM = "Foundation And Earth"


# Logging constants

INDENT_FILE = 6
INDENT_FILE_LOG = INDENT_FILE - 1
INDENT_PHASE = 20
LINE_WIDTH = 90

METADATA_PATH = "metadata/"

# Logging DIR constants
LOGS_DIR = "logs/"
LOGS_ANALYSIS = "logs/phase1_analysis/"
LOGS_CLEANING = "logs/phase1_cleaning/"
LOGS_CONVERSION = "logs/conversion/"


# other_constants

AUDIO_FILES = 0
ERR_FILE_REJECTED = False

STANDARDIZED_BOOK_PATH = BOOK_DIR + "Standardized_Audiobook"

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
