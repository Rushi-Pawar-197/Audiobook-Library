```
 █████╗ ██╗   ██╗██████╗ ██╗ ██████╗ ██████╗  ██████╗  ██████╗ ██╗  ██╗
 ██╔══██╗██║   ██║██╔══██╗██║██╔═══██╗██╔══██╗██╔═══██╗██╔═══██╗██║ ██╔╝
 ███████║██║   ██║██║  ██║██║██║   ██║██████╔╝██║   ██║██║   ██║█████╔╝ 
 ██╔══██║██║   ██║██║  ██║██║██║   ██║██╔══██╗██║   ██║██║   ██║██╔═██╗ 
 ██║  ██║╚██████╔╝██████╔╝██║╚██████╔╝██████╔╝╚██████╔╝╚██████╔╝██║  ██╗
 ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
                                                                     
                     ██╗     ██╗██████╗ ██████╗  █████╗ ██████╗ ██╗   ██╗                   
                     ██║     ██║██╔══██╗██╔══██╗██╔══██╗██╔══██╗╚██╗ ██╔╝                   
                     ██║     ██║██████╔╝██████╔╝███████║██████╔╝ ╚████╔╝                    
                     ██║     ██║██╔══██╗██╔══██╗██╔══██║██╔══██╗  ╚██╔╝                     
                     ███████╗██║██████╔╝██║  ██║██║  ██║██║  ██║   ██║                      
                     ╚══════╝╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    
 
 
        ───────◇  Analyze  ~  Clean  ~  Standardize  ◇───────

```

A Python and FFmpeg-based audiobook processing pipeline for cleaning, normalizing, converting, and organizing audiobook collections.

Audiobook Library is designed to take a batch of audiobook recordings with inconsistent formats, loudness levels, noise characteristics, and metadata, process them according to their individual requirements, and produce a consistent audiobook library.

The project uses a **batch-driven workflow**: audiobook directories and processing options are described in a CSV file, validated before processing begins, and then processed in a deterministic order.

---

## Features

- Batch processing of multiple audiobooks
- CSV-driven audiobook configuration
- Strict batch validation before processing
- Deterministic audiobook processing order
- Optional source preprocessing
- Multi-stage audio analysis and DSP processing
- Adaptive DSP processing based on recording characteristics
- Audiobook-wide loudness analysis and normalization
- Noise-floor and estimated signal-to-noise-ratio analysis
- Electrical hum detection and reduction
- Frequency-domain analysis
- Multiple DSP processing levels
- Persistent Stage 1 and Stage 2 processing metadata
- Resume-friendly Stage 3 cleaning
- Audio conversion to MP3 at 128 kbps
- Automatic track ordering and renaming where required
- Automatic ID3 metadata embedding
- Optional embedded cover artwork
- Detailed terminal output and persistent logs
- FFmpeg diagnostic logs for troubleshooting
- Standalone audiobook splitting utility
- Makefile-based setup, diagnostics, execution, and utilities

---

# How It Works

The project processes each audiobook through a multi-phase pipeline.

```text
Batch CSV
    │
    ▼
Batch Validation
    │
    ▼
┌─────────────────────────────────────┐
│ PHASE 1 — AUDIO CLEANING            │
│                                     │
│ Optional Preprocessing              │
│          ↓                          │
│ Stage 1 — Analyze                   │
│          ↓                          │
│ Stage 2 — Processing Plan           │
│          ↓                          │
│ Stage 3 — Cleaning / DSP Execution  │
└─────────────────────────────────────┘
    │
    ▼
PHASE 2 — AUDIO NORMALIZATION
    │
    ├── Convert supported formats to MP3
    └── Rename tracks when required
    │
    ▼
PHASE 3 — METADATA
    │
    ├── Write ID3 metadata
    └── Embed cover artwork when available
    │
    ▼
Processed Audiobook
```

The DSP pipeline deliberately separates **analysis**, **decision-making**, and **execution**. Stage 1 analyzes the source audio, Stage 2 generates the processing plan for the complete audiobook, and Stage 3 executes those persisted decisions.

---

# Installation

## Requirements

The project requires:

- Python 3
- FFmpeg
- FFprobe
- GNU Make (recommended)

FFmpeg and FFprobe must be available through the system `PATH`.

The Python dependencies are listed in `requirements.txt`.

### FFmpeg installation

`make setup` attempts to install FFmpeg automatically on supported Linux and macOS systems when it is missing. On Windows, FFmpeg must be installed separately and made available through `PATH`.

If automatic installation is unavailable on your system, install FFmpeg manually and ensure both `ffmpeg` and `ffprobe` can be executed from a terminal.

---

## Clone the Repository

```bash
git clone https://github.com/Rushi-Pawar-197/Audiobook-Library.git
cd Audiobook-Library
```

---

## Recommended Setup

Run:

```bash
make setup
```

The setup process:

1. Checks for FFmpeg and FFprobe.
2. Creates the Python virtual environment if necessary.
3. Detects and recreates an incomplete or incompatible virtual environment when necessary.
4. Installs the Python dependencies from `requirements.txt`.

The virtual-environment check is intentional: the existence of a `venv` directory alone does not mean that the environment is usable.

---

## Environment Diagnostics

To inspect the current environment without running the audiobook processor:

```bash
make doctor
```

This checks the system Python, virtual environment, pip, Python dependencies, FFmpeg, and FFprobe.

---

## Manual Setup

If GNU Make is unavailable, the project can be configured manually.

### Create a Virtual Environment

```bash
python3 -m venv venv
```

### Activate the Virtual Environment

#### Linux / macOS

```bash
source venv/bin/activate
```

#### Windows Command Prompt

```cmd
venv\Scripts\activate
```

#### Windows PowerShell

```powershell
venv\Scripts\Activate.ps1
```

### Install Dependencies

```bash
python -m pip install -r requirements.txt
```

---

# Batch Processing

Audiobook Library no longer uses the old single-book `config.py` workflow. Current processing is controlled by a **batch directory** and a CSV metadata file.

The batch directory is currently configured through `BATCH_DIR` in:

```text
utils/constants.py
```

`BATCH_DIR` is an implementation-level configuration value for now and may be moved to a more user-facing configuration mechanism in a future version.

---

## Batch Directory Structure

A batch directory should contain one CSV metadata file, one directory for each audiobook listed in the CSV, and optionally a `covers` directory.

A typical batch looks like:

```text
batch/
├── audiobook_metadata.csv
├── Dune/
│   ├── chapter 01.m4b
│   ├── chapter 02.m4b
│   └── ...
├── Foundation/
│   ├── chapter 01.mp3
│   ├── chapter 02.mp3
│   └── ...
└── covers/
    ├── Dune.jpg
    └── Foundation.png
```

The CSV filename itself is not fixed. The batch loader expects **exactly one CSV file** in the batch directory.

Extra audiobook directories that are not listed in the CSV are ignored during batch validation.

---

# Batch CSV

The CSV must contain exactly the required fields used by the current batch processor:

```text
book_id,AUTHOR,BOOK,PREPROCESS,PREPROCESS_TYPE,DSP_PROCESSING
```

Example:

```csv
book_id,AUTHOR,BOOK,PREPROCESS,PREPROCESS_TYPE,DSP_PROCESSING
1,Frank Herbert,Dune,y,1,y
2,Isaac Asimov,Foundation,n,1,y
3,Isaac Asimov,The Caves of Steel,n,1,n
```

## CSV Fields

| Field | Description |
|---|---|
| `book_id` | Unique positive natural number. It determines processing order. IDs must form a complete sequence from `1` to the number of books in the CSV. |
| `AUTHOR` | Author/artist value written to the audiobook metadata. Required. |
| `BOOK` | Audiobook title and the name used to locate the corresponding book directory and cover. Required and case-insensitively unique. |
| `PREPROCESS` | Whether source preprocessing is enabled: `y` or `n`. |
| `PREPROCESS_TYPE` | Preprocessing mode. Currently `1` or `2` when preprocessing is enabled. (refer section for info)|
| `DSP_PROCESSING` | Whether DSP processing is enabled: `y` or `n`. |

### `book_id`

`book_id` is the primary key for each audiobook entry and has two purposes:

1. It uniquely identifies the audiobook within the batch.
2. It defines the processing order.

The IDs must be positive natural numbers and must form a complete sequence beginning at `1`.

Valid:

```text
1, 2, 3, 4
```

Invalid:

```text
1, 2, 4
```

Invalid:

```text
1, 2, 2, 3
```

Invalid:

```text
0, 1, 2
```

The processor sorts the validated books by `book_id` before processing.

### `AUTHOR`

The author value is written to the final audio metadata as the artist.

It must not be empty.

### `BOOK`

The book name is used as the logical audiobook title and to locate the corresponding directory and cover artwork.

Book names must be unique within the CSV, case-insensitively.

### `PREPROCESS`

Set this to:

```text
y
```

to enable preprocessing, or:

```text
n
```

to skip it.

### `PREPROCESS_TYPE`

When `PREPROCESS=y`, the preprocessing type must currently be either:

```text
1
```

or:

```text
2
```

Where 1 is for "Disk-Subfolder" audiobook structure, and 2 is "In-order rename" audiobook structure.

When preprocessing is disabled, this field is not used for processing decisions.

### `DSP_PROCESSING`

Set this to `y` to run the DSP analysis/cleaning pipeline or `n` to skip DSP processing.

---

# Batch Validation

Before processing begins, the complete batch is validated.

Validation includes:

- A CSV metadata file must exist.
- Exactly one CSV file must be present in the batch directory.
- All required CSV fields must be present.
- `book_id` values must be positive natural numbers.
- `book_id` values must be unique.
- `book_id` values must form the complete sequence `1...N`.
- `AUTHOR` must not be empty.
- `BOOK` must not be empty.
- `BOOK` names must be unique, case-insensitively.
- `PREPROCESS` must be `y` or `n`.
- `PREPROCESS_TYPE` must be `1` or `2` when preprocessing is enabled.
- `DSP_PROCESSING` must be `y` or `n`.
- Every `BOOK` must have exactly one matching audiobook directory, ignoring case.

If batch validation fails, processing is aborted before any audiobook is processed.

After validation, the program displays the batch and asks for confirmation before starting processing.

---

# Audiobook Directories

Each audiobook listed in `BOOK` must have a corresponding directory directly inside the batch directory.

Directory matching is **case-insensitive**.

For example, if the CSV contains:

```text
BOOK = Dune
```

then a directory named any of the following will match:

```text
Dune/
dune/
DUNE/
```

More than one case-insensitive match is treated as an error.

---

# Cover Artwork

Cover artwork is optional.

If a `covers` directory exists, the cover filename must have the same base name as the corresponding `BOOK` directory, with matching performed case-insensitively.

Supported cover formats are:

```text
.jpg
.jpeg
.png
.webp
```

For example:

```text
batch/
├── Dune/
└── covers/
    └── dune.jpg
```

matches the audiobook directory `Dune/`.

A missing cover is **not a fatal validation error**. The user is warned, processing continues, and the final audiobook is produced without embedded cover artwork.

Multiple matching covers for the same audiobook are treated as a validation error.

---

# Running the Processor

Once the batch directory and CSV have been prepared, run:

```bash
make run
```

The application loads the batch, validates it, asks for confirmation, and processes each audiobook in `book_id` order.

The main application entry point is:

```text
main.py
```

---

# Processing Pipeline

## Phase 1 — Audio Cleaning

Phase 1 performs optional preprocessing followed by the DSP pipeline.

### Optional Preprocessing

The preprocessing stage is controlled independently for each audiobook through `PREPROCESS` and `PREPROCESS_TYPE`.

### Stage 1 — Analyze

Stage 1 analyzes every source audio file in the audiobook and persists the results to:

```text
metadata/stage1_metadata.json
```

Analysis includes measurements such as:

- Technical audio properties
- Loudness
- RMS levels
- Peak levels
- Noise-floor estimation
- Estimated signal-to-noise ratio
- Electrical hum
- Frequency-domain characteristics

FFprobe is used for technical inspection, while FFmpeg is used for audio analysis.

### Stage 2 — Processing

Stage 2 reads the complete Stage 1 dataset and generates a processing plan for the audiobook.

The resulting decisions are persisted to:

```text
metadata/stage2_metadata.json
```

Processing decisions can include different levels of cleaning depending on the characteristics of the recording, rather than applying the same aggressive filter chain to every file.

Stage 2 also makes the audiobook-wide loudness decision.

### Stage 3 — Cleaning

Stage 3 executes the persisted Stage 2 processing plans.

Existing completed output files can be treated as completed work, allowing this stage to resume without unnecessarily repeating previous processing.

---

# Loudness Normalization

Audiobook loudness is normalized toward a fixed library target of:

```text
-23 LUFS
```

The loudness processing also applies safety constraints:

- Maximum loudness boost: `+8 dB`
- True-peak limit/headroom target: `-1 dB`

The goal is to keep different audiobooks at a consistent listening level while preventing unusually quiet source material from receiving excessive gain.

## Loudness Analysis Performance

The loudness-analysis path has been optimized to reduce the amount of repeated audio decoding required during DSP analysis.

This substantially reduces the time spent on loudness normalization analysis while preserving the same processing objective.

---

# Long Audiobooks and DSP

DSP analysis is intentionally limited to audio files shorter than the configured maximum duration.

The current limit is:

```text
7200 seconds (2 hours)
```

Files at or beyond this limit are excluded from DSP analysis.

This is intentional: very large monolithic audiobook files can make DSP analysis disproportionately expensive. The standalone audiobook splitter can be used to divide such files into smaller parts before processing.

---

# Phase 2 — Audio Normalization

Phase 2 converts supported non-MP3 source formats into MP3.

The current output settings are:

```text
Format: MP3
Codec:  libmp3lame
Bitrate: 128 kbps
```

Supported source extensions include common formats such as:

```text
.mp3  .mp2  .aac  .m4a  .m4b
.flac .wav  .aiff .aif  .ape  .wv .tta
.ogg  .oga  .opus
.wma
.ac3  .eac3
.amr  .3gp  .3gpp
```

MP3 files do not need conversion.

When required, the project also performs audiobook track renaming/order normalization after conversion.

---

# Phase 3 — Metadata

Phase 3 writes metadata to the final MP3 files.

The following information is written:

- Title
- Artist / author
- Album / audiobook name
- Track number

Track numbers are derived from the filename where possible and otherwise fall back to the file's position in the sorted track list.

Cover artwork is embedded when a matching cover was found during batch validation.

---

# Audiobook Split Utility

The project includes a standalone utility for splitting large, monolithic audiobook files into smaller segments.

It is primarily intended for audiobooks that exceed the DSP duration limit or are otherwise inconvenient to process as a single file.

## Using the Splitter

The recommended Makefile interface is:

```bash
make split <file>
```

For example:

```bash
make split "/path/to/My Audiobook.m4b"
```

The underlying utility can also be run directly:

```bash
python utils/split.py "/path/to/My Audiobook.m4b"
```

The default segment length is:

```text
60 minutes
```

The default is configurable through:

```python
DEFAULT_PART_MINUTES = 60
```

in `utils/constants.py`.

The 60-minute value is the recommended default but is not a hard-coded limitation of the splitter.

## Split Behavior

The splitter:

- Uses FFmpeg stream copying (`-c copy`) rather than re-encoding the audio.
- Produces segments using the original file extension.
- Names segments using the pattern:

```text
Original Name - part 01.ext
Original Name - part 02.ext
...
```

- Verifies that output segments exist and are non-empty.
- Uses FFprobe to verify that each output segment contains an audio stream.
- Preserves the original file if splitting or verification fails.
- Removes the original file only after successful verification of the split output.

Because the splitter uses stream copying, it is designed to avoid unnecessary quality loss and re-encoding time.

---

# Logging

The project produces detailed terminal output and persistent logs.

## Terminal Output

Terminal output reports batch validation, audiobook progress, processing stages, warnings, errors, and completion status.

## Persistent Logs

Logs are stored under:

```text
logs/
├── complete_logs/
└── err_logs/
```

Per-audiobook error logs are maintained when processing failures occur.

## FFmpeg Diagnostics

FFmpeg diagnostic information is retained where appropriate to help investigate:

- Failed FFmpeg commands
- Decoding problems
- Processing errors
- Conversion failures
- Unexpected audio behavior

---

# Generated Files

The exact files generated depend on the audiobook and processing path, but important supporting data includes:

```text
metadata/
    stage1_metadata.json
    stage2_metadata.json
```

and project logs under:

```text
logs/
```

A processed audiobook also receives a `Standardized_Audiobook` output directory during the DSP pipeline before later phases operate on the standardized audio.

---

# Project Structure

A simplified project structure is:

```text
Audiobook-Library/
│
├── main.py
├── Makefile
├── requirements.txt
├── README.md
│
├── modules/
│   ├── Audio_DSP.py
│   ├── Audio_Normalization.py
│   └── Audio_Metadata.py
│
├── preprocessing/
│   ├── preprocessing.py
│   ├── in_order_rename.py
│   └── disk_subfolder_structure.py
│
├── utils/
│   ├── constants.py
│   ├── split.py
│   └── utility.py
│
├── logs/
└── assets/
```

## Important Files

### `main.py`

Main application entry point. It loads the batch, validates it, requests confirmation, and starts batch processing.

### `utils/constants.py`

Contains project-wide constants, including the current `BATCH_DIR`, DSP limits, loudness targets, supported audio extensions, and the default audiobook split length.

### `utils/utility.py`

Contains the batch loading and validation logic, processing orchestration, logging helpers, and other shared utilities.

### `modules/Audio_DSP.py`

Implements the Stage 1 analysis, Stage 2 processing-plan generation, and Stage 3 DSP execution pipeline.

### `modules/Audio_Normalization.py`

Handles conversion of supported audio formats to the project's standard MP3 output and performs track renaming when required.

### `modules/Audio_Metadata.py`

Writes final ID3 metadata and embeds cover artwork when available.

### `utils/split.py`

Standalone lossless audiobook splitting utility.

### `Makefile`

Provides the recommended command-line interface for setup, diagnostics, processing, splitting, and cleanup.

---

# Makefile Commands

| Command | Purpose |
|---|---|
| `make setup` | Check system dependencies, create/repair the virtual environment, and install Python dependencies. |
| `make doctor` | Diagnose the Python environment, dependencies, FFmpeg, and FFprobe. |
| `make run` | Run the batch audiobook processor. |
| `make split <file>` | Split one audiobook using the configured default segment length. |
| `make clean` | Remove Python `__pycache__` directories. |

---

# Typical Workflow

## 1. Set Up the Environment

```bash
make setup
```

## 2. Configure the Batch Directory

Set `BATCH_DIR` in:

```text
utils/constants.py
```

## 3. Prepare the Batch

Create a batch directory containing:

```text
batch/
├── audiobook_metadata.csv
├── Book One/
├── Book Two/
├── Book Three/
└── covers/
```

Ensure that the CSV contains valid sequential `book_id` values and that every `BOOK` entry has a matching audiobook directory.

## 4. Run Diagnostics if Needed

```bash
make doctor
```

## 5. Process the Batch

```bash
make run
```

The program validates the entire batch and asks for confirmation before processing begins.

## 6. Split Large Source Files When Necessary

For monolithic files that exceed the DSP duration limit:

```bash
make split "/path/to/large audiobook.m4b"
```

Then use the resulting segments as the source material for processing.

---

# Safety and File Handling

Audiobook processing modifies and creates files during several stages. For important or irreplaceable recordings, keep a separate backup of the original source material.

The splitter provides an additional safety measure: it verifies its generated segments before deleting the original monolithic file.

It is recommended to test the pipeline on a small batch before processing a large audiobook collection.

---

# Release History

## v2.2.0 — Audiobook Split Utility and Loudness Performance

- Added a standalone audiobook splitting utility.
- Added configurable split length with a 60-minute default.
- Split output is verified with FFprobe before the source file is removed.
- Improved the runtime of loudness normalization analysis by reducing unnecessary audio decoding work.
- Added handling for audiobook files that exceed the DSP analysis duration limit.
- Updated the project documentation to reflect the current batch-processing architecture.

## v2.1.0 — DSP Analysis Optimization and Audiobook-Wide Loudness Normalization

- Optimized DSP analysis.
- Added audiobook-wide loudness normalization.
- Introduced a fixed audiobook loudness target and loudness safety constraints.

## v2.0.1 — Logging and Reliability Improvements

- Improved logging presentation and terminal UX.
- Added logging-related fixes and reliability improvements.

## v2.0.0 — Unified Batch Audiobook Processing

- Introduced the unified batch audiobook processing architecture.
- Replaced the earlier single-audiobook workflow with CSV-driven batch processing.

## v1.1.1 — Logging and Terminal UX

- Improved logging and terminal presentation.

## v1.1.0 — Processing Architecture and Optimization

- Introduced the staged audiobook processing architecture.
- Added processing and performance improvements.

## v1.0.0 — Initial Baseline

- Initial Python-based audiobook processing pipeline.

---

# Notes

Audiobook Library is designed specifically for audiobook processing rather than general-purpose music production.

Source recordings can vary significantly in quality. Processing results therefore depend on factors such as:

- Original recording quality
- Background noise
- Electrical hum
- Dynamic range
- Source format
- Existing loudness characteristics

The DSP pipeline is intentionally conservative: it attempts to make processing decisions from measured characteristics rather than applying the same aggressive processing chain to every recording.
