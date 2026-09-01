# Audiobook Library

A Python and FFmpeg-based audiobook processing pipeline for cleaning, standardizing, converting, and organizing audiobook audio files.

The project analyzes audiobook recordings, evaluates their audio characteristics, applies an appropriate level of DSP processing, converts files where necessary, and embeds consistent metadata and cover artwork.

The goal is to take a collection of audiobook files with potentially inconsistent formats, loudness levels, noise characteristics, or metadata and produce a cleaner, more consistent audiobook library.

---

## Features

* Automated audiobook audio analysis
* Adaptive DSP processing based on the characteristics of individual audio files
* Loudness analysis and normalization
* Noise floor and estimated signal-to-noise ratio analysis
* Electrical hum detection and reduction
* Frequency-domain analysis
* Multiple processing levels based on detected audio quality
* Persistent analysis and processing metadata
* Resume-friendly multi-stage processing
* Audio conversion to MP3
* Automatic metadata embedding
* Artist, album, title, and track number metadata
* Embedded cover artwork
* Detailed terminal and persistent logging
* FFmpeg diagnostic logs for troubleshooting
* Makefile-based setup and execution
* Manual setup and execution as a fallback
* Minimal user configuration

---

# How It Works

The project processes an audiobook through a multi-phase pipeline.

```text
Raw Audiobook Files
        │
        ▼
Optional Preprocessing
        │
        ▼
Phase 1 — Analysis & DSP Processing
        │
        ├── Stage 1: Audio Analysis
        │
        ├── Stage 2: Processing Plan Generation
        │
        └── Stage 3: Processing Execution
        │
        ▼
Phase 2 — Audio Conversion
        │
        ▼
Phase 3 — Metadata & Cover Art
        │
        ▼
Processed Audiobook Library
```

The pipeline deliberately separates **analysis**, **decision-making**, and **processing**.

Audio characteristics are analyzed first, processing decisions are generated and stored, and the resulting processing plan is then executed without unnecessarily repeating the analysis.

---

# Installation

## Requirements

The project requires:

* Python 3
* FFmpeg, including FFprobe

FFmpeg and FFprobe must be installed and available through your system's `PATH`.

### Recommended

For the recommended setup and execution workflow, the project also uses:

* GNU Make

GNU Make is used as a convenience layer for automatically setting up the Python environment and running the project.

If `make` is unavailable or causes platform-specific issues, the project can also be set up and run manually.

---

## Clone the Repository

```bash
git clone https://github.com/Rushi-Pawar-197/Audiobook-Library
cd "Audiobook Library"
```

---

## Recommended Setup

Run:

```bash
make setup
```

This automatically creates the project's Python virtual environment, if necessary, and installs the required Python dependencies.

---

## Manual Setup

If GNU Make is unavailable or the Makefile does not work correctly on your system, the project can be set up manually.

### Create a Virtual Environment

```bash
python -m venv venv
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
pip install -r requirements.txt
```

---

# Usage

Using the project requires only three steps.

## 1. Configure the Audiobook

Open `config.py` and provide the required audiobook information:

```python
BOOK_DIR = ""
COVER_PATH = ""
ARTIST = ""
ALBUM = ""
```

### `BOOK_DIR`

The path to the directory containing the audiobook audio files.

### `COVER_PATH`

The path to the cover image that will be embedded into the processed audiobook files.

### `ARTIST`

The artist or author name to be written into the audio metadata.

### `ALBUM`

The album or audiobook title to be written into the audio metadata.

`config.py` is the user-facing configuration file. The remaining project constants are internal implementation values and do not normally need to be modified.

---

## 2. Ensure the Audiobook Files Are Ready

Ensure that `BOOK_DIR` points to the directory containing the audiobook files you want to process.

The project discovers and processes supported audio files according to the configured processing pipeline.

---

## 3. Run the Project

### Recommended

```bash
make run
```

This runs the project through the `main.py` entry point using the configuration provided in `config.py`.

### Manual

If you are using the manual setup method, activate the virtual environment and run:

```bash
python main.py
```

The manual method uses the same application entry point and processing pipeline as the Makefile-based workflow.

---

# Technical Pipeline

## Phase 1 — Audio Analysis and DSP Processing

Phase 1 is divided into three distinct stages.

---

## Stage 1 — Audio Analysis

Each audio file is analyzed before processing decisions are made.

The analysis includes measurements and estimates such as:

* Technical audio properties
* Loudness
* RMS levels
* Peak levels
* Noise floor estimation
* Estimated signal-to-noise ratio
* Electrical hum
* Frequency-domain characteristics

FFprobe is used to inspect audio properties, while FFmpeg is used for decoding and audio analysis.

The analysis results are persisted for use by later stages.

---

## Stage 2 — Processing Plan Generation

The analysis results are used to determine how aggressively each file should be processed.

The project evaluates characteristics such as:

* Noise severity
* Hum severity
* Loudness requirements
* Frequency characteristics

Based on these measurements, the pipeline generates a processing plan for each audio file.

The processing plans can select different cleaning levels:

* `minimal`
* `moderate`
* `standard`

This allows relatively clean recordings to avoid unnecessary processing while recordings with more significant issues can receive stronger treatment.

The resulting decisions are persisted so that the next stage can execute them directly.

---

## Stage 3 — Processing Execution

Stage 3 performs the actual audio processing.

Instead of repeating the complete analysis, this stage consumes the processing decisions generated previously.

Depending on the requirements of an individual file, processing can involve FFmpeg filters and operations such as:

* High-pass filtering
* Hum reduction
* Frequency correction
* Noise reduction
* Loudness adjustment

The processing pipeline therefore adapts its treatment to the characteristics of individual recordings instead of applying the same aggressive filter chain to every file.

---

# Audio Processing

## Loudness Processing

The project analyzes loudness using FFmpeg loudness measurement.

The processing pipeline is designed around a target loudness of approximately:

```text
-23 LUFS
```

Loudness adjustments also account for constraints intended to prevent excessive gain and undesirable output peaks.

---

## Noise Analysis and Reduction

The project estimates noise characteristics by examining relatively quiet and stable portions of a recording.

These measurements are used to estimate the noise floor and determine whether noise reduction is necessary.

When appropriate, FFmpeg-based noise reduction can be applied.

---

## Hum Detection

The frequency-domain analysis includes detection of electrical hum, particularly around common mains frequencies such as:

```text
50 Hz
60 Hz
```

The analysis also considers harmonic characteristics when evaluating hum.

When significant hum is detected, the processing plan can include appropriate corrective filtering.

---

## Frequency Analysis

The pipeline performs FFT-based frequency analysis to examine broad spectral characteristics of the recording.

These measurements contribute to the processing decisions generated for each audio file.

---

# Phase 2 — Audio Conversion

After DSP processing, audio files that require conversion are converted to the project's target output format.

The conversion stage produces MP3 output where necessary and helps create a more consistent audiobook library.

---

# Phase 3 — Metadata and Cover Art

After audio processing and conversion, metadata is applied to the final audio files.

The project can embed information such as:

* Track title
* Artist
* Album
* Track number
* Cover artwork

The artist and album information are configured through `config.py`.

The cover image specified by `COVER_PATH` is embedded into the processed audiobook files.

This ensures that the final audiobook files are not only processed consistently, but are also properly identifiable in audiobook and media applications.

---

# Persistent Processing Metadata

The processing pipeline stores intermediate metadata so that analysis, planning, and execution remain separate.

Generated processing information includes files such as:

```text
stage1_metadata.json
stage2_metadata.json
```

Conceptually:

```text
Stage 1
Audio Analysis
      │
      ▼
stage1_metadata.json
      │
      ▼
Stage 2
Processing Decisions
      │
      ▼
stage2_metadata.json
      │
      ▼
Stage 3
Processing Execution
```

This structure avoids unnecessary re-analysis and makes the multi-stage processing workflow easier to inspect and resume.

---

# Logging

The project produces detailed output throughout execution.

## Terminal Output

Terminal output is formatted for readability and provides visibility into the progress of the processing pipeline.

Processing stages, files, operations, and important events are reported as the project runs.

---

## Persistent Logs

Execution logs are stored in the project's logging directory.

The persistent logs provide a readable record of processing activity.

Terminal formatting and ANSI control sequences are stripped from file logs so they remain readable when opened directly in a text editor.

---

## FFmpeg Diagnostics

FFmpeg operations can produce detailed diagnostic information.

Additional logs are retained where appropriate to help investigate:

* Failed FFmpeg commands
* Processing errors
* Conversion issues
* Unexpected audio-processing behaviour

These logs can be useful when troubleshooting a particular audiobook file.

---

# Safety and File Handling

The project is designed as a multi-stage processing pipeline rather than a one-step transformation.

Files move through analysis, processing, conversion, and metadata stages before final processing is complete.

Intermediate metadata and processing results allow the pipeline to track progress across these stages.

However, audio processing can involve multiple file transformations. For important or irreplaceable audiobook files, maintaining a separate backup of the original files is always recommended.

It is also advisable to test the project on a small audiobook collection before processing a large or important library.

---

# Generated Files

During processing, the project can generate supporting files and directories.

Examples include:

```text
logs/
stage1_metadata.json
stage2_metadata.json
```

These files support logging, audio analysis, processing decisions, and execution of the multi-stage pipeline.

Additional intermediate files may be generated depending on the source audiobook formats and processing operations required.

---

# Project Structure

A simplified project structure is:

```text
Audiobook Library/
│
├── main.py
├── config.py
├── Makefile
├── requirements.txt
│
├── utils/
│   ├── constants.py
│   └── ...
│
├── logs/
│
└── ...
```

## Important Files

### `main.py`

The main application entry point.

The project is executed through this file when running:

```bash
make run
```

or manually:

```bash
python main.py
```

---

### `config.py`

The user-facing configuration file.

This is where the audiobook directory, cover artwork, artist, and album information are configured.

```python
BOOK_DIR = ""
COVER_PATH = ""
ARTIST = ""
ALBUM = ""
```

---

### `utils/constants.py`

Contains internal application constants used by the processing pipeline.

Users normally do not need to modify this file.

---

### `Makefile`

Provides the recommended interface for setting up and running the project.

```bash
make setup
make run
```

---

# Typical Workflow

A typical audiobook processing workflow looks like this:

```bash
# Set up the project
make setup
```

Configure the audiobook information in:

```text
config.py
```

Then run:

```bash
make run
```

The project then performs its configured processing pipeline:

```text
Analyze Audio
      ↓
Generate Processing Plans
      ↓
Process Audio
      ↓
Convert Files
      ↓
Apply Metadata
      ↓
Embed Cover Art
```

---

# Notes

This project is designed specifically around audiobook processing rather than general-purpose music production.

The DSP pipeline attempts to make processing decisions based on the characteristics of each recording instead of applying the same processing chain to every audio file.

Because source recordings can vary significantly in quality, processing results may depend on factors such as:

* Original recording quality
* Background noise
* Electrical hum
* Source format
* Dynamic range
* Loudness characteristics

For important or irreplaceable audiobook files, keeping a separate backup of the original files is always recommended.
