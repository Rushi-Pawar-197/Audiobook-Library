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

    FFmpeg diagnostics are stored separately for this operation.
    Recoverable decoder diagnostics are retained as a warning; a failed
    decode still raises an error and stops processing of this file.

    We use mono 16 kHz because this is more than enough
    for the measurements we currently need.
    """

    file_path = Path(file_path)

    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(file_path),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "-",
    ]

    stderr_log = os.path.join(const.LOGS_ANALYSIS / f"{file_path.name}.stderr")

    result, diagnostic_log = util.run_ffmpeg(
        command,
        stderr_log,
        stdout=subprocess.PIPE,
    )

    if result.returncode != 0:
        log_location = f" See {diagnostic_log}." if diagnostic_log else ""
        raise RuntimeError(f"FFmpeg audio analysis failed.{log_location}")

    if diagnostic_log is not None:
        util.log_warning(
            f"FFmpeg reported decoding issues while analyzing {file_path.name}. "
            f"See {diagnostic_log}.\n",
            indent=const.INDENT_FILE_LOG,
        )

    audio = np.frombuffer(result.stdout, dtype=np.float32)

    if len(audio) == 0:
        raise ValueError("Audio decoding produced no samples.")

    duration = len(audio) / sample_rate

    if duration < 1.0:
        raise ValueError(
            f"Audio is too short for DSP analysis ({duration:.3f} seconds)."
        )

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

    The returned tuple also contains the RMS energy of the
    selected quiet material so callers do not need to scan
    the selected samples a second time just to calculate the
    noise floor.
    """

    window_size = int(sample_rate * window_seconds)

    if len(audio) < window_size:
        return audio, dbfs(audio)

    measurements = []

    for start in range(0, len(audio) - window_size, window_size):

        window = audio[start : start + window_size]

        # Calculate the window energy once.  The same energy
        # is reused for the window RMS and, when this window is
        # selected, the final quiet-section RMS.
        mean_square = np.mean(window**2)

        if mean_square <= 1e-24:
            level = -120.0
        else:
            level = 10 * math.log10(mean_square)

        # Divide the window into smaller pieces.
        sub_size = max(1, window_size // 10)

        sub_levels = []

        for sub_start in range(0, window_size - sub_size + 1, sub_size):

            sub = window[sub_start : sub_start + sub_size]

            sub_mean_square = np.mean(sub**2)

            if sub_mean_square <= 1e-24:
                sub_levels.append(-120.0)
            else:
                sub_levels.append(10 * math.log10(sub_mean_square))

        variation = max(sub_levels) - min(sub_levels)

        measurements.append(
            {
                "start": start,
                "end": start + window_size,
                "level": level,
                "variation": variation,
                "mean_square": mean_square,
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
        if (
            item["level"] <= quiet_threshold
            and item["level"] > const.NOISE_FLOOR_SILENCE_THRESHOLD_DBFS
            and item["variation"] <= 6
        )
    ]

    # If the recording does not contain enough perfectly
    # stable regions, relax the stability requirement.

    if len(candidates) < 3:

        candidates = [
            item
            for item in measurements
            if (
                item["level"] <= quiet_threshold
                and item["level"] > const.NOISE_FLOOR_SILENCE_THRESHOLD_DBFS
            )
        ]

    # Still nothing useful?
    if not candidates:
        return audio, dbfs(audio)

    # --------------------------------------------------------
    # Use several quiet sections rather than one.
    # --------------------------------------------------------

    candidates.sort(key=lambda item: item["level"])

    selected = candidates[: max(3, min(10, len(candidates)))]

    quiet_audio = np.concatenate(
        [audio[item["start"] : item["end"]] for item in selected]
    )

    # All selected windows have the same size, so the RMS of
    # their concatenation is the square root of the mean of
    # their already-calculated mean-square values.
    quiet_mean_square = np.mean([item["mean_square"] for item in selected])

    if quiet_mean_square <= 1e-24:
        quiet_rms = -120.0
    else:
        quiet_rms = 10 * math.log10(quiet_mean_square)

    return quiet_audio, quiet_rms


# ============================================================
# FREQUENCY ANALYSIS
# ============================================================


def calculate_spectrum(audio, sample_rate):
    """
    Calculate a normalized linear-magnitude frequency spectrum.

    The magnitude is normalized relative to the strongest
    frequency component. Power calculations are performed
    from the linear magnitude before any dB conversion.
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

    return frequencies, magnitude


def band_energy(frequencies, magnitude, low, high):
    """
    Calculate average relative power within a frequency band.
    """

    mask = (frequencies >= low) & (frequencies < high)

    if not np.any(mask):
        return -120.0

    # Convert linear magnitude to power.
    power = magnitude[mask] ** 2

    average_power = np.mean(power)

    if average_power <= 1e-24:
        return -120.0

    return 10 * math.log10(average_power)


def analyze_frequency_bands(audio, sample_rate):
    """
    Analyze broad frequency regions.

    Values are relative to the strongest frequency component,
    so they can be compared between recordings.
    """
    frequencies, magnitude = calculate_spectrum(audio, sample_rate)

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

        result[name] = round(
            band_energy(frequencies, magnitude, low, high),
            2,
        )

    return result


# ============================================================
# HUM DETECTION
# ============================================================


def calculate_hum_spectrum(audio, sample_rate):
    """
    Prepare the FFT spectrum used by hum detection.

    All hum measurements use the same audio, sample rate,
    30-second limit, DC removal, Hann window, and FFT.
    Calculate that shared spectrum once instead of repeating
    the same work for every fundamental and harmonic.
    """

    if len(audio) == 0:
        return None, None

    max_samples = min(len(audio), sample_rate * 30)

    audio = audio[:max_samples]

    # Remove DC offset.
    audio = audio - np.mean(audio)

    # Window the signal to reduce spectral leakage.
    window = np.hanning(len(audio))

    spectrum = np.fft.rfft(audio * window)

    frequencies = np.fft.rfftfreq(len(audio), 1 / sample_rate)

    magnitude = np.abs(spectrum)

    return frequencies, magnitude


def calculate_hum_strength_from_spectrum(frequencies, magnitude, frequency):
    """
    Measure a specific hum frequency using a precomputed FFT spectrum.
    """

    if frequencies is None or magnitude is None:
        return {
            "frequency_level_db": -120.0,
            "neighbor_level_db": -120.0,
            "prominence_db": 0.0,
        }

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


def calculate_hum_strength(audio, sample_rate, frequency):
    """
    Measure how much a specific frequency stands out
    compared with its immediate neighboring frequencies.

    This compatibility wrapper retains the original function
    interface.  analyze_hum() uses the shared spectrum directly
    so that repeated FFT calculations are avoided.
    """

    frequencies, magnitude = calculate_hum_spectrum(audio, sample_rate)

    return calculate_hum_strength_from_spectrum(frequencies, magnitude, frequency)


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

    # All fundamentals and harmonics use the exact same input
    # signal and FFT preparation. Calculate that spectrum once.
    frequencies, magnitude = calculate_hum_spectrum(audio, sample_rate)

    for fundamental in (50, 60):

        # ----------------------------------------------------
        # Fundamental
        # ----------------------------------------------------

        fundamental_result = calculate_hum_strength_from_spectrum(
            frequencies, magnitude, fundamental
        )

        harmonics = []

        # ----------------------------------------------------
        # Harmonics
        # ----------------------------------------------------

        for harmonic in range(2, 7):

            frequency = fundamental * harmonic

            if frequency >= sample_rate / 2:
                break

            harmonic_result = calculate_hum_strength_from_spectrum(
                frequencies, magnitude, frequency
            )

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

    util.log(f"{file_path.name}\n", indent=const.INDENT_FILE)

    # --------------------------------------------------------
    # FILE INFORMATION
    # --------------------------------------------------------

    info = get_audio_info(file_path)

    if info["duration"] <= 0:
        raise ValueError(f"Invalid audio duration: {info['duration']} seconds.")

    util.log(
        f"Duration\t\t:  {util.format_time(info['duration'])}", indent=const.INDENT_FILE
    )
    util.log(f"Sample rate\t:  {info['sample_rate']} Hz", indent=const.INDENT_FILE)
    util.log(f"Channels\t\t:  {info['channel_layout']}", indent=const.INDENT_FILE)

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

    quiet_audio, noise_floor = find_stable_quiet_sections(audio, sample_rate)

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
        "file": file_path.name,
        "technical": {
            "duration": info["duration"],
            "sample_rate": info["sample_rate"],
            "channels": info["channels"],
        },
        "levels": {
            "rms_dbfs": overall_level,
            "peak_dbfs": peak_level,
        },
        "noise": {
            "noise_floor_dbfs": noise_floor,
            "snr_db": estimated_snr,
        },
        "hum": hum,
        "loudness": loudness,
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

    snr_db = analysis["noise"]["snr_db"]
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


def clean_audio(
    input_file,
    processing_decision,
):
    """
    Stage 3 — Execute the processing plan for one audio file.

    Stage 3 deliberately consumes only Stage 2 processing metadata.
    It does not re-analyze the source or make processing decisions.
    """

    input_file = Path(input_file)

    output_dir = Path(const.STANDARDIZED_BOOK_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)

    cleaning = processing_decision["cleaning"]

    processing_level = cleaning["level"]
    noise_reduction = cleaning["noise_reduction_db"]
    hum_reduction = cleaning["hum_reduction_db"]
    highpass = cleaning["highpass_hz"]
    detected_hum = cleaning.get("hum_frequency_hz")
    loudness = processing_decision.get("loudness") or {}
    gain_db = float(loudness.get("gain_db") or 0.0)

    filters = []

    if highpass is not None:
        filters.append(f"highpass=f={highpass}")

    if hum_reduction > 0 and detected_hum is not None:
        filters.append(f"equalizer=f={detected_hum}:t=q:w=2:g=-{hum_reduction}")

    if noise_reduction > 0:
        filters.append(f"afftdn=nr={noise_reduction}:tn=1")

    # Loudness gain is deliberately last so the Stage 2 decision applies
    # after the conventional cleaning filters.
    if abs(gain_db) > 0.001:
        filters.append(f"volume={gain_db:+.2f}dB")

    filter_chain = ",".join(filters)

    util.log(f"Processing level :  {processing_level}\n", indent=const.INDENT_FILE)
    util.log(f"Noise reduction  :  {noise_reduction:.2f} dB", indent=const.INDENT_FILE)
    util.log(f"Hum reduction    :  {hum_reduction:.2f} dB", indent=const.INDENT_FILE)
    util.log(f"Loudness gain    :  {gain_db:+.2f} dB", indent=const.INDENT_FILE)
    if highpass is not None:
        util.log(f"High-pass        :  {highpass} Hz\n", indent=const.INDENT_FILE)
    else:
        util.log("High-pass        :  none\n", indent=const.INDENT_FILE)

    util.print_filter_chain(filter_chain)

    if not filter_chain:
        util.log_ok("No cleaning required.", indent=const.INDENT_FILE_LOG)
        output_file = output_dir / input_file.name

        try:
            shutil.copy2(input_file, output_file)
        except Exception as error:
            print()
            util.log_error(
                f"Could not copy audio file -> {error}",
                indent=const.INDENT_FILE_LOG,
            )
            return False

        util.log_ok("Audio copied as it is.", indent=const.INDENT_FILE_LOG)
        return True

    output_file = output_dir / f"{input_file.stem}.wav"

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

    stderr_log = const.LOGS_CLEANING / f"{input_file.name}.stderr"

    result, diagnostic_log = util.run_ffmpeg(command, stderr_log)

    if result.returncode != 0:
        print()
        util.log_error(
            "FFmpeg audio cleaning failed.",
            indent=const.INDENT_FILE_LOG,
        )
        if diagnostic_log is not None:
            util.log(f" See {diagnostic_log}", indent=const.INDENT_FILE_LOG)
        return False

    if not output_file.exists():
        print()
        util.log_error(
            "FFmpeg audio cleaning completed without producing the output file.",
            indent=const.INDENT_FILE_LOG,
        )
        if diagnostic_log is not None:
            util.log(f" See {diagnostic_log}", indent=const.INDENT_FILE_LOG)
        return False

    if diagnostic_log is not None:
        util.log_warning(
            f"FFmpeg reported decoding issues while cleaning {input_file.name}. "
            f"See {diagnostic_log}.\n",
            indent=const.INDENT_FILE_LOG,
        )
        util.log_ok(
            f"Cleaned → {output_file.name}",
            indent=const.INDENT_FILE_LOG,
        )
        return False

    util.log_ok(
        f"Cleaned → {output_file.name}",
        indent=const.INDENT_FILE_LOG,
    )
    return True


# ============================================================
# STAGE 2 — AUDIOBOOK-WIDE LOUDNESS
# ============================================================


def calculate_loudness_gain(source_lufs, source_true_peak_db):
    """Calculate the final per-file loudness gain.

    The audiobook uses one fixed target loudness.  Positive gain is
    constrained by both a maximum boost and the measured source true peak.
    Negative gain is unrestricted by those positive-gain limits.
    """

    if source_lufs is None:
        return 0.0, None

    desired_gain = const.AUDIOBOOK_TARGET_LUFS - source_lufs

    if desired_gain <= 0:
        return round(desired_gain, 2), None

    limits = [(const.MAX_LOUDNESS_BOOST_DB, "maximum_boost")]

    if source_true_peak_db is not None:
        true_peak_headroom = const.TRUE_PEAK_LIMIT_DB - source_true_peak_db
        limits.append((true_peak_headroom, "true_peak_limit"))

    positive_limit, reason = min(limits, key=lambda item: item[0])

    final_gain = min(desired_gain, positive_limit)

    if final_gain < 0:
        final_gain = 0.0

    return round(final_gain, 2), (reason if final_gain < desired_gain else None)


# ============================================================
# STAGE 2 — BUILD ONE FILE'S PROCESSING PLAN
# ============================================================


def build_processing_plan(analysis):
    """
    Build the Stage 2 processing plan for one analyzed file.

    This function makes decisions but does not process audio.
    """

    decision = determine_processing_level(analysis)

    processing_level = decision["processing_level"]
    noise_severity = decision["noise_severity"]
    hum_severity = decision["hum_severity"]
    overall_severity = decision["overall_severity"]

    noise_reduction = calculate_noise_reduction(
        noise_severity,
        processing_level,
    )

    hum_reduction = calculate_hum_reduction(
        hum_severity,
        processing_level,
    )

    highpass = calculate_highpass(
        overall_severity,
        processing_level,
    )

    detected_hum = analysis["hum"].get("detected_hum")
    if detected_hum is not None:
        detected_hum = int(detected_hum)

    source_loudness = analysis.get("loudness") or {}
    source_lufs = source_loudness.get("integrated_loudness")
    source_true_peak_db = source_loudness.get("true_peak")

    # The target is audiobook-wide, so every valid file receives its
    # gain decision against the same Stage 2 target.
    gain_db, gain_limit_reason = calculate_loudness_gain(
        source_lufs,
        source_true_peak_db,
    )

    return {
        "file": analysis["file"],
        "cleaning": {
            "level": processing_level,
            "noise_reduction_db": noise_reduction,
            "hum_reduction_db": hum_reduction,
            "hum_frequency_hz": detected_hum,
            "highpass_hz": highpass,
        },
        "diagnostics": {
            "overall_severity": overall_severity,
            "noise_severity": noise_severity,
            "hum_severity": hum_severity,
        },
        "loudness": {
            "source_lufs": source_lufs,
            "source_true_peak_db": source_true_peak_db,
            "source_loudness_range": source_loudness.get("loudness_range"),
            "gain_db": gain_db,
            "gain_limited_by": gain_limit_reason,
        },
    }


# ============================================================
# METADATA HELPERS
# ============================================================


def _write_json(path, data):
    """Write JSON metadata atomically enough for stage-level persistence."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4, ensure_ascii=False)
        handle.write("\n")

    temporary.replace(path)


def _load_json(path):
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


# ============================================================
# STAGE 1 — ANALYZE ALL AUDIO
# ============================================================


def stage1_analyze(book_path, audio_files):
    """
    Stage 1 — Analyze every source audio file and persist one
    audiobook-level metadata JSON document.
    """

    book_path = Path(book_path)
    metadata_path = Path(const.METADATA_PATH, "stage1_metadata.json")

    util.stage_title_card("Stage 1 : Analyze", type="stage", char="-")

    files = []
    failed = 0

    for index, audio_file in enumerate(audio_files, start=1):
        print()
        util.log(f"[cyan1]\n[{index}/{len(audio_files)}][/cyan1]")

        audio_file = Path(audio_file)
        error_log = const.LOGS_ANALYSIS / f"{audio_file.name}.error"

        try:
            files.append(analyze_audio(audio_file))
        except Exception as error:
            failed += 1
            const.ERR_FILE_REJECTED = True
            util.log_error(
                f" processing {audio_file.name}: {error}",
                indent=const.INDENT_FILE_LOG,
            )
            util.log_file_error(
                f"Audio analysis failed for: {audio_file.name}\n"
                f"Error: {type(error).__name__}: {error}",
                error_log,
            )

    if failed:
        util.log_warning("Some files failed analysis. See the error logs for details.")

    metadata = {
        "files": files,
    }

    _write_json(metadata_path, metadata)

    util.batch_summary(total=len(audio_files), good=len(files), dirty=failed)

    util.log_ok(
        f"Stage 1 metadata written → {metadata_path.name}",
    )
    util.log_ok("Stage 1 complete")

    return metadata


# ============================================================
# STAGE 2 — BUILD ALL PROCESSING PLANS
# ============================================================


def stage2_process(book_path, stage1_metadata):
    """
    Stage 2 — Interpret the complete Stage 1 dataset and persist one
    audiobook-level processing metadata JSON document.

    Stage 2 also makes the audiobook-wide loudness decision.
    Every valid file is planned against one fixed target LUFS and a
    true-peak ceiling.
    """

    book_path = Path(book_path)
    metadata_path = Path(os.path.join(const.METADATA_PATH, "stage2_metadata.json"))

    util.stage_title_card("Stage 2 : Processing", type="stage", char="-")

    plans = []
    total = len(stage1_metadata["files"])
    failed = 0

    for index, analysis in enumerate(stage1_metadata["files"], start=1):
        print()
        util.log(f"[cyan1]\n[{index}/{total}][/cyan1]")
        util.log(f"{analysis['file']}\n", indent=const.INDENT_FILE)

        try:
            plan = build_processing_plan(analysis)
            plans.append(plan)

            util.log(
                f"Noise severity   :  {plan['diagnostics']['noise_severity']:.3f}",
                indent=const.INDENT_FILE,
            )
            util.log(
                f"Hum severity     :  {plan['diagnostics']['hum_severity']:.3f}",
                indent=const.INDENT_FILE,
            )
            util.log(
                f"Overall severity :  {plan['diagnostics']['overall_severity']:.3f}",
                indent=const.INDENT_FILE,
            )
            util.log(
                f"Processing level :  {plan['cleaning']['level']}",
                indent=const.INDENT_FILE,
            )
            util.log(
                f"Source loudness  :  {plan['loudness']['source_lufs']} LUFS",
                indent=const.INDENT_FILE,
            )
            util.log(
                f"Loudness gain    :  {plan['loudness']['gain_db']:+.2f} dB\n",
                indent=const.INDENT_FILE,
            )

        except Exception as error:
            failed += 1
            const.ERR_FILE_REJECTED = True
            util.log_error(
                f" processing {analysis['file']}: {error}",
                indent=const.INDENT_FILE_LOG,
            )

    metadata = {
        "loudness": {
            "target_lufs": const.AUDIOBOOK_TARGET_LUFS,
            "true_peak_limit_db": const.TRUE_PEAK_LIMIT_DB,
            "max_boost_db": const.MAX_LOUDNESS_BOOST_DB,
        },
        "files": plans,
    }

    _write_json(metadata_path, metadata)

    util.batch_summary(total=total, good=len(plans), dirty=failed)

    util.log_ok(
        f"Stage 2 metadata written → {metadata_path.name}",
    )
    util.log_ok("Stage 2 complete")

    return metadata


# ============================================================
# STAGE 3 — EXECUTE ALL PROCESSING PLANS
# ============================================================


def stage3_clean(book_path, stage2_metadata):
    """
    Stage 3 — Execute the persisted processing plans.

    Existing output files are treated as completed work so that Stage 3
    can resume after an interrupted run.
    """

    book_path = Path(book_path)

    audio_files = [
        os.path.join(book_path, file)
        for file in os.listdir(book_path)
        if file.lower().endswith(tuple(const.SUPPORTED_AUDIO_EXTENSIONS))
    ]

    audio_by_name = {
        Path(audio_file).name: Path(audio_file) for audio_file in audio_files
    }

    print()
    util.stage_title_card("Stage 3 : Cleaning", type="stage", char="-")

    successful = 0
    failed = 0

    output_dir = book_path / "Standardized_Audiobook"
    output_dir.mkdir(parents=True, exist_ok=True)
    const.STANDARDIZED_BOOK_PATH = output_dir

    for index, plan in enumerate(stage2_metadata["files"], start=1):
        print()
        util.log(f"[cyan1]\n[{index}/{len(stage2_metadata['files'])}][/cyan1]")

        filename = plan["file"]
        input_file = audio_by_name.get(filename, book_path / filename)

        if not input_file.exists():
            failed += 1
            const.ERR_FILE_REJECTED = True
            util.log_error(
                f" source file not found: {filename}",
                indent=const.INDENT_FILE_LOG,
            )
            continue

        cleaning = plan["cleaning"]
        loudness = plan.get("loudness") or {}
        gain_db = float(loudness.get("gain_db") or 0.0)
        needs_processing = (
            cleaning["noise_reduction_db"] > 0
            or cleaning["hum_reduction_db"] > 0
            or cleaning["highpass_hz"] is not None
            or abs(gain_db) > 0.001
        )

        if not needs_processing:
            output_file = output_dir / filename
        else:
            output_file = output_dir / f"{Path(filename).stem}.wav"

        if output_file.exists():
            successful += 1
            util.log_ok(
                f"Already complete → {output_file.name}",
                indent=const.INDENT_FILE_LOG,
            )
            continue

        try:
            success = clean_audio(input_file, plan)
            if success:
                successful += 1
            else:
                failed += 1
        except Exception as error:
            failed += 1
            const.ERR_FILE_REJECTED = True
            util.log_error(
                f" processing {filename}: {error}",
                indent=const.INDENT_FILE_LOG,
            )

    util.batch_summary(
        total=len(stage2_metadata["files"]), good=successful, dirty=failed
    )

    util.log_ok("Stage 3 complete")

    return failed == 0


# ============================================================
# AUDIOBOOK PIPELINE
# ============================================================


def audio_cleaning(book_path, dsp_processing):
    """
    Run the audiobook through the true batch Stage 1 → Stage 2 → Stage 3
    architecture.

    Stage 1 analyzes every file first and writes stage1_metadata.json.
    Stage 2 reads that complete dataset, creates all processing plans, and
    writes stage2_metadata.json.
    Stage 3 executes those persisted plans and can resume from existing
    output files.
    """

    if dsp_processing == "n":
        print()
        util.log_info("Audio Cleaning sequence skipped")
        const.STANDARDIZED_BOOK_PATH = book_path
        return

    else:
        const.STANDARDIZED_BOOK_PATH = Path(book_path) / "Standardized_Audiobook"

    book_path = Path(book_path)

    if not book_path.is_dir():
        raise NotADirectoryError(book_path)
    audio_files = [
        os.path.join(book_path, file)
        for file in os.listdir(book_path)
        if file.lower().endswith(tuple(const.SUPPORTED_AUDIO_EXTENSIONS))
    ]
    audio_file_path = [Path(file) for file in audio_files]

    if not audio_file_path:
        raise ValueError("No audio files were provided for audiobook processing.")

    util.stage_title_card("PHASE 1 : AUDIO CLEANING", type="phase", char="=")

    # --------------------------------------------------------
    # STAGE 1
    # --------------------------------------------------------

    stage1_metadata = stage1_analyze(book_path, audio_file_path)

    # --------------------------------------------------------
    # STAGE 2
    # --------------------------------------------------------

    stage2_metadata = stage2_process(book_path, stage1_metadata)

    # --------------------------------------------------------
    # STAGE 3
    # --------------------------------------------------------

    stage3_clean(book_path, stage2_metadata)
    print()
    util.log_ok("Phase 1 complete")
