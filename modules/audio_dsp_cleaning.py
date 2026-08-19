import subprocess
import json
import math
import os
import numpy as np
import shutil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import constants as const
from utils import utility as util

# ============================================================
# AUDIO ANALYSIS
# ============================================================


def run_command(command):
    """
    Run a system command and return stdout.
    """

    result = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed:\n{' '.join(command)}\n\n" f"{result.stderr}"
        )

    return result.stdout


# ============================================================
# BASIC FILE INFORMATION
# ============================================================


def get_audio_info(file_path):
    """
    Get basic audio information using ffprobe.
    """

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        file_path,
    ]

    data = json.loads(run_command(command))

    audio_stream = next(
        stream for stream in data["streams"] if stream["codec_type"] == "audio"
    )

    return {
        "codec": audio_stream.get("codec_name"),
        "sample_rate": int(audio_stream["sample_rate"]),
        "channels": int(audio_stream["channels"]),
        "channel_layout": audio_stream.get("channel_layout"),
        "bit_rate": int(
            audio_stream.get("bit_rate") or data["format"].get("bit_rate") or 0
        ),
        "duration": float(
            audio_stream.get("duration") or data["format"].get("duration") or 0
        ),
    }


# ============================================================
# LOAD AUDIO
# ============================================================


def load_audio_for_analysis(file_path, sample_rate=16000):
    """
    Decode audio through FFmpeg.

    We use mono 16 kHz because this is more than enough
    for the measurements we currently need.
    """

    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        file_path,
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "-",
    ]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace"))

    audio = np.frombuffer(result.stdout, dtype=np.float32)

    return audio, sample_rate


# ============================================================
# LEVEL MEASUREMENTS
# ============================================================


def dbfs(samples):
    """
    Calculate RMS level in dBFS.
    """

    if len(samples) == 0:
        return -120.0

    rms = np.sqrt(np.mean(samples**2))

    if rms <= 1e-12:
        return -120.0

    return 20 * math.log10(rms)


def peak_dbfs(samples):
    """
    Calculate peak level in dBFS.
    """

    if len(samples) == 0:
        return -120.0

    peak = np.max(np.abs(samples))

    if peak <= 1e-12:
        return -120.0

    return 20 * math.log10(peak)


# ============================================================
# LOUDNESS
# ============================================================


def calculate_loudness(file_path):
    """
    Ask FFmpeg's loudnorm filter for loudness measurements.
    """

    command = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        file_path,
        "-af",
        "loudnorm=print_format=json",
        "-f",
        "null",
        "-",
    ]

    result = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    stderr = result.stderr

    start = stderr.rfind("{")

    if start == -1:
        return None

    try:
        data = json.loads(stderr[start:])

        return {
            "integrated_loudness": float(data.get("input_i", 0)),
            "true_peak": float(data.get("input_tp", 0)),
            "loudness_range": float(data.get("input_lra", 0)),
        }

    except (json.JSONDecodeError, ValueError):
        return None


# ============================================================
# NOISE FLOOR
# ============================================================


def find_stable_quiet_sections(audio, sample_rate, window_seconds=1.0):
    """
    Find stable, quiet regions of the recording.

    Instead of simply taking the quietest 10% of the audio,
    this function looks for windows that are both:

        1. quiet
        2. relatively stable in volume

    Stable quiet regions are more likely to represent the
    actual background noise rather than speech tails,
    breaths, clicks, etc.
    """

    window_size = int(sample_rate * window_seconds)

    if len(audio) < window_size:
        return audio

    measurements = []

    for start in range(0, len(audio) - window_size, window_size):

        window = audio[start : start + window_size]

        level = dbfs(window)

        # Divide the window into smaller pieces.
        sub_size = max(1, window_size // 10)

        sub_levels = []

        for sub_start in range(0, window_size - sub_size + 1, sub_size):

            sub = window[sub_start : sub_start + sub_size]

            sub_levels.append(dbfs(sub))

        variation = max(sub_levels) - min(sub_levels)

        measurements.append(
            {
                "start": start,
                "end": start + window_size,
                "level": level,
                "variation": variation,
            }
        )

    # --------------------------------------------------------
    # First determine what counts as "quiet".
    #
    # We use the lower portion of the level distribution
    # rather than an absolute dBFS threshold.
    # --------------------------------------------------------

    levels = np.array([item["level"] for item in measurements])

    quiet_threshold = np.percentile(levels, 30)

    # --------------------------------------------------------
    # Among quiet sections, prefer stable sections.
    # --------------------------------------------------------

    candidates = [
        item
        for item in measurements
        if (item["level"] <= quiet_threshold and item["variation"] <= 6)
    ]

    # If the recording does not contain enough perfectly
    # stable regions, relax the stability requirement.
    if len(candidates) < 3:

        candidates = [item for item in measurements if item["level"] <= quiet_threshold]

    # Still nothing useful?
    if not candidates:
        return audio

    # --------------------------------------------------------
    # Use several quiet sections rather than one.
    # --------------------------------------------------------

    candidates.sort(key=lambda item: item["level"])

    selected = candidates[: max(3, min(10, len(candidates)))]

    quiet_audio = np.concatenate(
        [audio[item["start"] : item["end"]] for item in selected]
    )

    return quiet_audio


# ============================================================
# FREQUENCY ANALYSIS
# ============================================================


def calculate_spectrum(audio, sample_rate):
    """
    Calculate a normalized frequency spectrum.

    The result is expressed relative to the strongest
    frequency component rather than using raw FFT magnitude.
    This makes the numbers meaningful and comparable.
    """

    if len(audio) == 0:
        return None, None

    max_samples = min(len(audio), sample_rate * 30)

    audio = audio[:max_samples]

    audio = audio - np.mean(audio)

    window = np.hanning(len(audio))

    spectrum = np.fft.rfft(audio * window)

    frequencies = np.fft.rfftfreq(len(audio), 1 / sample_rate)

    magnitude = np.abs(spectrum)

    if np.max(magnitude) > 0:
        magnitude = magnitude / np.max(magnitude)

    magnitude_db = 20 * np.log10(np.maximum(magnitude, 1e-12))

    return frequencies, magnitude_db


def band_energy(frequencies, spectrum_db, low, high):
    """
    Calculate average relative energy within a frequency band.
    """

    mask = (frequencies >= low) & (frequencies < high)

    if not np.any(mask):
        return None

    # Convert dB back to linear magnitude.
    linear = 10 ** (spectrum_db[mask] / 20)

    average = np.mean(linear)

    if average <= 1e-12:
        return -120.0

    return 20 * math.log10(average)


def analyze_frequency_bands(audio, sample_rate):
    """
    Analyze broad frequency regions.

    Values are relative to the strongest frequency component,
    so they can be compared between recordings.
    """

    frequencies, spectrum = calculate_spectrum(audio, sample_rate)

    if frequencies is None:
        return {}

    bands = {
        "sub_bass_20_50hz": (20, 50),
        "low_50_100hz": (50, 100),
        "low_mid_100_250hz": (100, 250),
        "mid_250_1000hz": (250, 1000),
        "presence_1_4khz": (1000, 4000),
        "high_4_8khz": (4000, 8000),
        "air_8_12khz": (8000, 12000),
    }

    result = {}

    for name, (low, high) in bands.items():

        result[name] = round(band_energy(frequencies, spectrum, low, high), 2)

    return result


# ============================================================
# HUM DETECTION
# ============================================================


def calculate_hum_strength(audio, sample_rate, frequency):
    """
    Measure how much a specific frequency stands out
    compared with its immediate neighboring frequencies.

    This is better for hum detection than comparing the
    frequency against the strongest frequency in the entire
    recording.

    Returns:
        {
            "frequency_level_db": ...,
            "neighbor_level_db": ...,
            "prominence_db": ...
        }

    'prominence_db' tells us how much the target frequency
    stands out from its surroundings.
    """

    if len(audio) == 0:
        return {
            "frequency_level_db": -120.0,
            "neighbor_level_db": -120.0,
            "prominence_db": 0.0,
        }

    # Use up to 30 seconds.
    max_samples = min(len(audio), sample_rate * 30)

    audio = audio[:max_samples]

    # Remove DC offset.
    audio = audio - np.mean(audio)

    # Window the signal to reduce spectral leakage.
    window = np.hanning(len(audio))

    spectrum = np.fft.rfft(audio * window)

    frequencies = np.fft.rfftfreq(len(audio), 1 / sample_rate)

    magnitude = np.abs(spectrum)

    # --------------------------------------------------------
    # Find the FFT bin closest to the target frequency.
    # --------------------------------------------------------

    target_index = np.argmin(np.abs(frequencies - frequency))

    # --------------------------------------------------------
    # Measure the target frequency.
    #
    # We use a small region around the target instead of
    # exactly one FFT bin.
    # --------------------------------------------------------

    target_mask = (frequencies >= frequency - 1.5) & (frequencies <= frequency + 1.5)

    target_energy = np.mean(magnitude[target_mask] ** 2)

    # --------------------------------------------------------
    # Measure the frequencies immediately surrounding the
    # target.
    #
    # Example for 60 Hz:
    #
    # 55–58 Hz   ← neighbors
    # 60 Hz      ← target
    # 62–65 Hz   ← neighbors
    #
    # We deliberately leave a gap around the target so that
    # the hum itself doesn't contaminate the reference.
    # --------------------------------------------------------

    neighbor_mask = (
        (frequencies >= frequency - 8) & (frequencies <= frequency - 3)
    ) | ((frequencies >= frequency + 3) & (frequencies <= frequency + 8))

    neighbor_energy = np.mean(magnitude[neighbor_mask] ** 2)

    if target_energy <= 1e-20:
        target_db = -120.0
    else:
        target_db = 10 * math.log10(target_energy)

    if neighbor_energy <= 1e-20:
        neighbor_db = -120.0
    else:
        neighbor_db = 10 * math.log10(neighbor_energy)

    prominence = target_db - neighbor_db

    return {
        "frequency_level_db": target_db,
        "neighbor_level_db": neighbor_db,
        "prominence_db": prominence,
    }


def analyze_hum(audio, sample_rate):
    """
    Detect possible 50 Hz or 60 Hz electrical hum.

    Hum is classified into three levels:

        NONE
        WEAK
        STRONG

    The primary measurement is how strongly the 50/60 Hz
    frequency stands out from its immediate surroundings.

    Harmonics are measured and returned as additional
    information, but they are NOT required for detection.
    """

    results = {}

    for fundamental in (50, 60):

        # ----------------------------------------------------
        # Fundamental
        # ----------------------------------------------------

        fundamental_result = calculate_hum_strength(audio, sample_rate, fundamental)

        harmonics = []

        # ----------------------------------------------------
        # Harmonics
        # ----------------------------------------------------

        for harmonic in range(2, 7):

            frequency = fundamental * harmonic

            if frequency >= sample_rate / 2:
                break

            harmonic_result = calculate_hum_strength(audio, sample_rate, frequency)

            harmonics.append(
                {
                    "frequency": frequency,
                    "level_db": round(harmonic_result["frequency_level_db"], 2),
                    "prominence_db": round(harmonic_result["prominence_db"], 2),
                }
            )

        results[fundamental] = {
            "level_db": round(fundamental_result["frequency_level_db"], 2),
            "neighbor_level_db": round(fundamental_result["neighbor_level_db"], 2),
            "prominence_db": round(fundamental_result["prominence_db"], 2),
            "harmonics": harmonics,
        }

    # ========================================================
    # CLASSIFY HUM
    # ========================================================

    def classify(prominence):

        if prominence < 6:

            return "none"

        elif prominence < 18:

            return "weak"

        else:

            return "strong"

    classification_50 = classify(results[50]["prominence_db"])

    classification_60 = classify(results[60]["prominence_db"])

    # --------------------------------------------------------
    # Choose the stronger candidate.
    # --------------------------------------------------------

    candidates = []

    if classification_50 != "none":

        candidates.append((50, results[50]["prominence_db"], classification_50))

    if classification_60 != "none":

        candidates.append((60, results[60]["prominence_db"], classification_60))

    if not candidates:

        detected_hum = None
        hum_strength = "none"

    else:

        detected = max(candidates, key=lambda item: item[1])

        detected_hum = detected[0]
        hum_strength = detected[2]

    return {
        "50hz": results[50],
        "60hz": results[60],
        "50hz_classification": classification_50,
        "60hz_classification": classification_60,
        "detected_hum": detected_hum,
        "hum_strength": hum_strength,
    }


# ============================================================
# MAIN ANALYSIS
# ============================================================


def analyze_audio(file_path):
    """
    Analyze an audiobook without modifying it.

    This function ONLY measures the audio.

    It does not:
        - clean the audio
        - modify the original
        - choose a processing level
        - apply FFmpeg filters
    """

    file_path = Path(file_path)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)

    print(" " * 6,f"{file_path.name}\n")

    # --------------------------------------------------------
    # FILE INFORMATION
    # --------------------------------------------------------

    info = get_audio_info(file_path)

    print(" " * 6,f"Duration\t\t:  {util.format_time(info['duration'])}")

    print(" " * 6,f"Sample rate\t:  {info['sample_rate']} Hz")

    print(" " * 6,f"Channels\t\t:  {info['channel_layout']}\n")    

    # --------------------------------------------------------
    # LOAD AUDIO
    # --------------------------------------------------------

    audio, sample_rate = load_audio_for_analysis(file_path)

    # --------------------------------------------------------
    # LEVELS
    # --------------------------------------------------------

    overall_level = dbfs(audio)
    peak_level = peak_dbfs(audio)

    # --------------------------------------------------------
    # NOISE FLOOR
    # --------------------------------------------------------

    quiet_audio = find_stable_quiet_sections(audio, sample_rate)

    noise_floor = dbfs(quiet_audio)

    estimated_snr = overall_level - noise_floor

    # --------------------------------------------------------
    # LOUDNESS
    # --------------------------------------------------------

    loudness = calculate_loudness(file_path)

    # --------------------------------------------------------
    # HUM
    # --------------------------------------------------------

    hum = analyze_hum(quiet_audio, sample_rate)

    # --------------------------------------------------------
    # FREQUENCY BANDS
    # --------------------------------------------------------

    bands = analyze_frequency_bands(audio, sample_rate)

    # --------------------------------------------------------
    # RETURN RESULTS
    # --------------------------------------------------------

    return {
        "file": file_path,
        "info": info,
        "levels": {
            "rms_dbfs": overall_level,
            "peak_dbfs": peak_level,
        },
        "noise": {
            "noise_floor_dbfs": noise_floor,
            "estimated_snr_db": estimated_snr,
        },
        "loudness": loudness,
        "hum": hum,
        "frequency_bands": bands,
    }


# ============================================================
# STAGE 2 — DETERMINE PROCESSING LEVEL
# ============================================================


def calculate_noise_severity(snr_db):
    """
    Convert estimated SNR into a noise-severity score.

    Score:
        0.0 = essentially clean
        1.0 = extremely noisy
    """

    if snr_db >= 45:
        return 0.0

    if snr_db >= 35:
        return (45 - snr_db) / 10 * 0.20

    if snr_db >= 30:
        return 0.20 + (35 - snr_db) / 5 * 0.20

    if snr_db >= 20:
        return 0.40 + (30 - snr_db) / 10 * 0.30

    if snr_db >= 10:
        return 0.70 + (20 - snr_db) / 10 * 0.30

    return 1.0


def calculate_hum_severity(hum_strength):
    """
    Convert hum classification into a severity score.

    NONE   -> 0.00
    WEAK   -> 0.35
    STRONG -> 1.00
    """

    hum_strength = hum_strength.lower()

    if hum_strength == "none":
        return 0.0

    if hum_strength == "weak":
        return 0.35

    if hum_strength == "strong":
        return 1.0

    # Unknown classification:
    # remain conservative and assume no confirmed defect.
    return 0.0


def determine_processing_level(analysis):
    """
    Determine the required conventional audio-cleaning level.

    Returns diagnostic information so that Stage 2 can be
    evaluated and tuned during development.
    """

    snr_db = analysis["noise"]["estimated_snr_db"]
    hum_strength = analysis["hum"]["hum_strength"]

    # --------------------------------------------------------
    # Individual severity measurements
    # --------------------------------------------------------

    noise_severity = calculate_noise_severity(snr_db)
    hum_severity = calculate_hum_severity(hum_strength)

    # --------------------------------------------------------
    # Combine severity
    # --------------------------------------------------------

    overall_severity = min(1.0, noise_severity + (0.50 * hum_severity))

    # --------------------------------------------------------
    # Determine processing level
    # --------------------------------------------------------

    if overall_severity < 0.30:
        processing_level = "minimal"

    elif overall_severity < 0.65:
        processing_level = "moderate"

    else:
        processing_level = "standard"

    return {
        "processing_level": processing_level,
        "overall_severity": overall_severity,
        "noise_severity": noise_severity,
        "hum_severity": hum_severity,
    }


# ============================================================
# STAGE 3 — AUDIO CLEANING
# ============================================================


def calculate_noise_reduction(noise_severity, processing_level):
    """
    Calculate FFmpeg afftdn noise-reduction strength.

    noise_severity:
        0.0 = essentially clean
        1.0 = extremely noisy

    processing_level:
        minimal / moderate / standard

    Returns:
        Noise reduction amount in dB.
    """

    max_reduction = {
        "minimal": 8.0,
        "moderate": 14.0,
        "standard": 20.0,
    }

    maximum = max_reduction.get(processing_level, 8.0)

    # Severity acts directly as the weight.
    reduction = noise_severity * maximum

    return round(reduction, 2)


def calculate_hum_reduction(hum_severity, processing_level):
    """
    Calculate hum attenuation in dB.

    hum_severity:
        0.0 = no hum
        1.0 = strong hum

    Returns:
        Hum attenuation in dB.
    """

    max_attenuation = {
        "minimal": 8.0,
        "moderate": 14.0,
        "standard": 20.0,
    }

    maximum = max_attenuation.get(processing_level, 8.0)

    attenuation = hum_severity * maximum

    return round(attenuation, 2)


def calculate_highpass(overall_severity, processing_level):
    """
    Calculate a conservative high-pass cutoff.

    overall_severity controls how much low-frequency
    cleanup is appropriate.

    Returns:
        Cutoff frequency in Hz.
        None means no high-pass filter.
    """

    if overall_severity <= 0:
        return None

    max_cutoff = {
        "minimal": 50,
        "moderate": 60,
        "standard": 70,
    }

    maximum = max_cutoff.get(processing_level, 50)

    # Start at 30 Hz and move toward the profile maximum
    # according to overall severity.
    cutoff = 30 + (maximum - 30) * overall_severity

    return round(cutoff, 1)


def build_filter_chain(
    processing_level,
    noise_severity,
    hum_severity,
    overall_severity,
    detected_hum,
):
    """
    Build the FFmpeg audio filter chain for Stage 3.
    """

    filters = []

    # --------------------------------------------------------
    # 1. HIGH-PASS FILTER
    # --------------------------------------------------------

    highpass = calculate_highpass(overall_severity, processing_level)

    if highpass is not None:
        filters.append(f"highpass=f={highpass}")

    # --------------------------------------------------------
    # 2. HUM REMOVAL
    # --------------------------------------------------------

    hum_reduction = calculate_hum_reduction(hum_severity, processing_level)

    if hum_reduction > 0:

        if detected_hum == "50":
            hum_frequency = 50

        elif detected_hum == "60":
            hum_frequency = 60

        else:
            hum_frequency = None

        if hum_frequency is not None:
            filters.append(
                f"equalizer="
                f"f={hum_frequency}:"
                f"t=q:"
                f"w=2:"
                f"g=-{hum_reduction}"
            )

    # --------------------------------------------------------
    # 3. BROADBAND NOISE REDUCTION
    # --------------------------------------------------------

    noise_reduction = calculate_noise_reduction(noise_severity, processing_level)

    if noise_reduction > 0:
        filters.append(f"afftdn=" f"nr={noise_reduction}:" f"tn=1")

    # --------------------------------------------------------
    # FINAL FILTER CHAIN
    # --------------------------------------------------------

    return ",".join(filters)


def clean_audio(
    input_file,
    processing_decision,
    analysis,
):
    """
    Stage 3 — Clean an audiobook audio file.

    The cleaned file is written to an 'output' directory
    located alongside the input file.

    Parameters
    ----------
    input_file : str or Path
        Original source audio file.

    processing_decision : dict
        Output from determine_processing_level().

    analysis : dict
        Output from analyze_audio().

    Returns
    -------
    bool
        True if processing succeeded.
        False if FFmpeg failed.
    """

    input_file = Path(input_file)

    # --------------------------------------------------------
    # CREATE OUTPUT DIRECTORY
    # --------------------------------------------------------

    output_dir = input_file.parent / "Standardized_Audiobook"
    output_dir.mkdir(parents=True, exist_ok=True)

    # output_file = output_dir / input_file.name
    output_file = output_dir / f"{input_file.stem}.wav"

    # --------------------------------------------------------
    # READ STAGE 2 DECISION
    # --------------------------------------------------------

    processing_level = processing_decision["processing_level"]

    noise_severity = processing_decision["noise_severity"]

    hum_severity = processing_decision["hum_severity"]

    overall_severity = processing_decision["overall_severity"]

    # --------------------------------------------------------
    # READ STAGE 1 HUM INFORMATION
    # --------------------------------------------------------

    detected_hum = analysis["hum"].get("detected_hum")

    if detected_hum is not None:
        detected_hum = str(detected_hum).replace("hz", "").strip()

    # --------------------------------------------------------
    # BUILD FILTER CHAIN
    # --------------------------------------------------------

    filter_chain = build_filter_chain(
        processing_level=processing_level,
        noise_severity=noise_severity,
        hum_severity=hum_severity,
        overall_severity=overall_severity,
        detected_hum=detected_hum,
    )

    # --------------------------------------------------------
    # DISPLAY DECISION
    # --------------------------------------------------------


    print(" " * 6,f"Noise severity   :  {noise_severity:.3f}")
    print(" " * 6,f"Hum severity     :  {hum_severity:.3f}")
    print(" " * 6,f"Overall severity :  {overall_severity:.3f}\n")
    print(" " * 6,f"Processing level :  {processing_level}\n")

    util.print_filter_chain(filter_chain)

    # --------------------------------------------------------
    # NO PROCESSING REQUIRED
    # --------------------------------------------------------

    if not filter_chain:
        util.log("\n"+" " * 5+"[bright_green][OK][/bright_green] No cleaning required.")

        output_file = output_dir / input_file.name

        try:
            shutil.copy2(input_file, output_file)

        except Exception as error:
            print()
            util.log_error(" Could not copy audio file.")
            print(error)

            return False

        util.log("\n"+" " * 5+"[bright_green][OK][/bright_green] Audio copied as it is.")

        return True

    # --------------------------------------------------------
    # PROCESS AUDIO
    # --------------------------------------------------------

    else:

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(input_file),
            "-map",
            "0:a",
            "-af",
            filter_chain,
            "-c:a",
            "pcm_s16le",
            str(output_file),
        ]

    # --------------------------------------------------------
    # RUN FFMPEG
    # --------------------------------------------------------

    try:

        subprocess.run(command, check=True)

    except subprocess.CalledProcessError as error:

        print()
        util.log_error(" FFmpeg audio cleaning failed.")
        print(error)

        return False

    util.log("\n"+" " * 5+f"[bright_green][OK][/bright_green] Cleaned → {output_file.name}")

    return True


# ============================================================
# PROCESS ONE AUDIO FILE
# ============================================================


def process_audio_file(audio_file):
    """
    Run the complete audiobook audio-cleaning pipeline
    for a single audio file.

    Stage 1 → Stage 2 → Stage 3
    """

    # --------------------------------------------------------
    # STAGE 1 — ANALYZE AUDIO
    # --------------------------------------------------------

    analysis = analyze_audio(str(audio_file))

    # --------------------------------------------------------
    # STAGE 2 — DETERMINE PROCESSING LEVEL
    # --------------------------------------------------------

    processing_decision = determine_processing_level(analysis)

    # --------------------------------------------------------
    # STAGE 3 — CLEAN AUDIO
    # --------------------------------------------------------

    success = clean_audio(str(audio_file), processing_decision, analysis)

    return success


# ============================================================
# PROCESS AUDIOBOOK DIRECTORY
# ============================================================


def audiobook_cleaning(book_path):
    """
    Process all supported audio files in an audiobook directory.

    Each file independently goes through:

        Stage 1 → Stage 2 → Stage 3
    """

    book_path = Path(book_path)

    if not book_path.is_dir():
        raise NotADirectoryError(book_path)

    # --------------------------------------------------------
    # FIND AUDIO FILES
    # --------------------------------------------------------

    audio_files = const.AUDIO_FILES

    print()
    print("=" * 70)
    util.log(" " * 20+"[bold][dark_turquoise]PHASE 1 : AUDIO CLEANING[/dark_turquoise][/bold]")
    print("=" * 70, "\n")

    # --------------------------------------------------------
    # PROCESS EACH FILE
    # --------------------------------------------------------

    successful = 0
    failed = 0

    for index, audio_file in enumerate(audio_files, start=1):

        print()
        util.log(f"[cyan1]\n[{index}/{len(audio_files)}][/cyan1]")

        try:

            success = process_audio_file(audio_file)

            if success:
                successful += 1
            else:
                failed += 1

        except Exception as error:

            failed += 1

            print()
            util.log_error(f" processing  {audio_file.name}:")
            print(error)

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("-" * 70)

    util.log(f" Total      : [bold][white]{len(audio_files)}[/bold][/white]")
    util.log(f" Successful : [bold][green4]{successful}[/bold][/green4]")
    util.log(f" Failed     : [bold][red3]{failed}[/bold][/red3]")

    print("-" * 70)
