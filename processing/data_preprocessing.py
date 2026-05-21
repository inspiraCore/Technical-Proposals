#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script for organizing RFP/TP text files and normalizing Arabic text.

Main features:
- Read DATA.zip, extract it to a folder, then process all .txt files inside.
- Organize and match RFP (PR_) and TP_ files by shared numeric code.
- Enforce consistent naming convention (e.g. PR_07.txt, TP_07.txt).
- Verify readability and convert to UTF-8.
- Clean and normalize Arabic text:
  * Remove diacritics, tatweel, noise characters (#, *, —, •, ·, -, O, etc.).
  * Normalize Arabic letters (ى→ي, ة→ه, أ/إ/آ→ا, etc.).
  * Normalize digits (Arabic ↔ English; configurable).
  * Reduce spaces, blank lines, and noisy lines while preserving headings.
  * Strip heading numbers like "61- برنامج العمل" → "برنامج العمل".
  * Remove leading bullet "o " at the start of lines.
  * Preserve important tags like TP# for technical offers.
"""

import logging
import re
import sys
import unicodedata
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

# Path to the ZIP file containing the data (must be next to this script)
ZIP_PATH = Path(__file__).parent / "DATA.zip"

# Folder where the ZIP will be extracted
EXTRACT_DIR = Path(__file__).parent / "DATA_EXTRACTED"

# Base directory for processing (after extraction)
BASE_DIR = EXTRACT_DIR

# File extensions to process
TEXT_EXTENSIONS = {".txt"}

# Prefixes used to identify RFP and TP files in names
RFP_PREFIXES = ("PR", "RFP")
TP_PREFIXES = ("TP",)

# Whether to actually rename files (if False, only logs what would happen)
DRY_RUN_RENAME = False

# Digits normalization target: "western" → 0123456789, "arabic" → ٠١٢٣٤٥٦٧٨٩
DIGIT_TARGET = "western"  # change to "arabic" if you want Arabic-Indic digits

# Whether to overwrite the original file with cleaned content
OVERWRITE_IN_PLACE = True  # overwrite extracted .txt files in place

# Directory where cleaned copies will be written if not overwriting in place
CLEAN_OUTPUT_SUBDIR = "cleaned"  # used only if OVERWRITE_IN_PLACE = False

# -----------------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------------

logger = logging.getLogger("rfp_tp_normalizer")


def setup_logging(level=logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(fmt)
    logger.setLevel(level)
    logger.addHandler(handler)


# -----------------------------------------------------------------------------
# ZIP EXTRACTION
# -----------------------------------------------------------------------------

def ensure_extracted(zip_path: Path, extract_dir: Path) -> None:
    """
    Ensure that the ZIP file is extracted into extract_dir.
    If extract_dir does not exist, extract the ZIP there.
    """
    if not zip_path.exists():
        logger.error("ZIP file not found: %s", zip_path)
        sys.exit(1)

    if extract_dir.exists() and extract_dir.is_dir():
        logger.info("Using existing extracted directory: %s", extract_dir)
        return

    logger.info("Extracting %s to %s", zip_path, extract_dir)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    logger.info("Extraction completed.")


# -----------------------------------------------------------------------------
# FILE DISCOVERY & MATCHING
# -----------------------------------------------------------------------------

CODE_PATTERN = re.compile(
    r"\b(?P<prefix>PR|RFP|TP)[_\-]?(?P<code>\d+)\b", re.IGNORECASE
)


def extract_code_parts(name: str) -> Optional[Tuple[str, int]]:
    """
    Extract (prefix, numeric_code) from filename.

    Example:
      'PR_07_somefile.txt' → ('PR', 7)
      'TP07-offer.txt'     → ('TP', 7)
    """
    m = CODE_PATTERN.search(name)
    if not m:
        return None
    prefix = m.group("prefix").upper()
    code_str = m.group("code")
    try:
        code = int(code_str)
    except ValueError:
        return None
    return prefix, code


def discover_text_files(base_dir: Path) -> List[Path]:
    files: List[Path] = []
    for p in base_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS:
            files.append(p)
    return files


def classify_files(files: List[Path]) -> Dict[int, Dict[str, List[Path]]]:
    """
    Group files by numeric code and role (RFP/TP), based on filename prefixes.
    Returns mapping: code → {"RFP": [...], "TP": [...]}
    """
    result: Dict[int, Dict[str, List[Path]]] = {}
    for f in files:
        parts = extract_code_parts(f.name)
        if not parts:
            logger.warning("Could not extract code from %s", f)
            continue
        prefix, code = parts

        if prefix in RFP_PREFIXES:
            role = "RFP"
        elif prefix in TP_PREFIXES:
            role = "TP"
        else:
            logger.warning("Unknown prefix for %s (prefix=%s)", f, prefix)
            continue

        if code not in result:
            result[code] = {"RFP": [], "TP": []}
        result[code][role].append(f)
    return result


def standard_name(prefix: str, code: int, suffix: str = "") -> str:
    """
    Build standardized filename:
        PR_07.txt, TP_07.txt, etc.
    """
    if suffix:
        return f"{prefix.upper()}_{code:02d}_{suffix}.txt"
    return f"{prefix.upper()}_{code:02d}.txt"


def rename_pairs(pairs: Dict[int, Dict[str, List[Path]]]) -> None:
    """
    Enforce naming convention, log mismatches.
    """
    for code, roles in pairs.items():
        rfps = roles.get("RFP", [])
        tps = roles.get("TP", [])

        if not rfps and not tps:
            continue

        if not rfps:
            logger.warning("Code %02d: has TP but no RFP", code)
        if not tps:
            logger.warning("Code %02d: has RFP but no TP", code)

        # Choose the first file as canonical in each group
        if rfps:
            rfp = rfps[0]
            new_name = standard_name("PR", code)
            rename_file(rfp, new_name)

        if tps:
            tp = tps[0]
            new_name = standard_name("TP", code)
            rename_file(tp, new_name)


def rename_file(path: Path, new_name: str) -> None:
    target = path.with_name(new_name)
    if target == path:
        return
    logger.info("Rename: %s → %s", path.name, target.name)
    if DRY_RUN_RENAME:
        return
    # Ensure we do not overwrite an existing distinct file
    if target.exists():
        logger.error("Target already exists, skipping: %s", target)
        return
    path.rename(target)


# -----------------------------------------------------------------------------
# ENCODING & READING
# -----------------------------------------------------------------------------

CANDIDATE_ENCODINGS = ["utf-8", "cp1256", "cp1252", "iso-8859-6"]


def read_text_with_fallback(path: Path) -> Tuple[str, str]:
    """
    Try multiple encodings; return (text, encoding_used).
    Always returns text normalized to NFC.
    """
    raw = path.read_bytes()
    last_error = None
    for enc in CANDIDATE_ENCODINGS:
        try:
            text = raw.decode(enc)
            text = unicodedata.normalize("NFC", text)
            if enc.lower() != "utf-8":
                logger.info("Re-decoded %s using %s", path, enc)
            return text, enc
        except UnicodeDecodeError as e:
            last_error = e
            continue
    logger.error("Failed to decode %s with tried encodings. Last error: %s", path, last_error)
    text = raw.decode("utf-8", errors="replace")
    text = unicodedata.normalize("NFC", text)
    return text, "utf-8 (errors=replace)"


def write_utf8_text(path: Path, text: str, base_dir: Path) -> None:
    """
    Write UTF-8 text either overwriting the original file or into a `cleaned` subdir.
    """
    if OVERWRITE_IN_PLACE:
        out_path = path
    else:
        rel = path.relative_to(base_dir)
        out_path = base_dir / CLEAN_OUTPUT_SUBDIR / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")


# -----------------------------------------------------------------------------
# ARABIC NORMALIZATION UTILITIES
# -----------------------------------------------------------------------------

# Arabic diacritics
ARABIC_DIACRITICS_RE = re.compile(
    r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]"
)

# Tatweel / elongation
TATWEEL_RE = re.compile(r"\u0640")

# Unwanted characters (outside protected patterns)
UNWANTED_CHARS_RE = re.compile(r"[·\-O#*•▪●■□◆◇▶➤—–]+")

# Multiple spaces & blank lines
MULTI_SPACE_RE = re.compile(r"[ \t]+")
MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

# Arabic letters normalization map
ARABIC_CHAR_MAP = {
    ord("أ"): "ا",
    ord("إ"): "ا",
    ord("آ"): "ا",
    ord("ؤ"): "و",
    ord("ئ"): "ي",
    ord("ى"): "ي",
    ord("ة"): "ه",
}

# Digits mapping
ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
EXT_ARABIC_INDIC_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
WESTERN_DIGITS = "0123456789"

ARABIC_TO_WESTERN = str.maketrans(
    dict(zip(ARABIC_INDIC_DIGITS, WESTERN_DIGITS))
    | dict(zip(EXT_ARABIC_INDIC_DIGITS, WESTERN_DIGITS))
)
WESTERN_TO_ARABIC = str.maketrans(dict(zip(WESTERN_DIGITS, ARABIC_INDIC_DIGITS)))


def remove_diacritics(text: str) -> str:
    return ARABIC_DIACRITICS_RE.sub("", text)


def remove_tatweel(text: str) -> str:
    return TATWEEL_RE.sub("", text)


def normalize_arabic_letters(text: str) -> str:
    return text.translate(ARABIC_CHAR_MAP)


def normalize_digits(text: str, target: str = "western") -> str:
    if target == "western":
        return text.translate(ARABIC_TO_WESTERN)
    elif target == "arabic":
        t = text.translate(ARABIC_TO_WESTERN)
        return t.translate(WESTERN_TO_ARABIC)
    return text


# -----------------------------------------------------------------------------
# PRESERVING SPECIAL TAGS (TP#… etc.)
# -----------------------------------------------------------------------------

SPECIAL_TAG_RE = re.compile(r"\bTP[#_\-]?\d+\b", re.IGNORECASE)


def protect_special_tags(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Replace TP-related tags with placeholders so we do not damage them
    when removing unwanted characters like '#'.
    """
    mapping: Dict[str, str] = {}
    idx = 0

    def repl(match: re.Match) -> str:
        nonlocal idx
        original = match.group(0)
        key = f"__TP_TAG_{idx}__"
        mapping[key] = original
        idx += 1
        return key

    protected_text = SPECIAL_TAG_RE.sub(repl, text)
    return protected_text, mapping


def restore_special_tags(text: str, mapping: Dict[str, str]) -> str:
    for key, original in mapping.items():
        text = text.replace(key, original)
    return text


# -----------------------------------------------------------------------------
# LINE CLEANING & HEADING PRESERVATION
# -----------------------------------------------------------------------------

ARABIC_LETTER_RE = re.compile(r"[\u0600-\u06FF]")

# Heading number patterns:
# "61- برنامج العمل", "3. الأهداف", "1) مقدمة"
HEADING_NUMBER_PREFIX_RE = re.compile(r"^\s*\d+\s*[-\.\):،:]?\s*(.+)$")
# "مقدمة 1", "المخرجات (3)"
HEADING_NUMBER_SUFFIX_RE = re.compile(r"^(.+?)\s*[-\.\(:،:]?\s*\d+\s*$")

# Remove leading "o " bullet at start of line: "o text..." → "text..."
BULLET_O_PREFIX_RE = re.compile(r"^\s*o\s+(?=\S)")


def strip_heading_numbers(line: str) -> str:
    """
    Remove leading or trailing numbers from heading-like lines.
    Examples:
      '1- مقدمة'      -> 'مقدمة'
      'مقدمة 1'       -> 'مقدمة'
      '3. الأهداف'    -> 'الأهداف'
      'المخرجات (3)'  -> 'المخرجات'
    """
    m = HEADING_NUMBER_PREFIX_RE.match(line)
    if m:
        line = m.group(1)

    m = HEADING_NUMBER_SUFFIX_RE.match(line)
    if m:
        line = m.group(1)

    return line.strip()


def is_heading_like(line: str) -> bool:
    """
    Treat a line as heading if:
    - It contains Arabic letters and
    - Length after stripping > 2
    """
    stripped = line.strip()
    if len(stripped) <= 2:
        return False
    return bool(ARABIC_LETTER_RE.search(stripped))


def is_noisy_line(line: str) -> bool:
    """
    Consider line as noise if, after trimming:
    - Empty OR
    - Contains almost no letters/digits and is mainly punctuation.
    """
    stripped = line.strip()
    if not stripped:
        return True
    if not re.search(r"[A-Za-z0-9\u0600-\u06FF]", stripped):
        return True
    return False


def clean_structure(text: str) -> str:
    """
    Normalize spaces inside lines, drop noisy lines,
    remove bullet 'o' at line start, and collapse excessive blank lines
    while preserving headings.
    """
    text = MULTI_SPACE_RE.sub(" ", text)

    lines = [ln.rstrip() for ln in text.splitlines()]

    cleaned_lines: List[str] = []
    for ln in lines:
        ln = BULLET_O_PREFIX_RE.sub("", ln)

        if is_heading_like(ln):
            ln = strip_heading_numbers(ln)
            if not ln.strip():
                continue
            cleaned_lines.append(ln)
        else:
            if is_noisy_line(ln):
                continue
            cleaned_lines.append(ln)

    text = "\n".join(cleaned_lines)
    text = MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip() + "\n"


# -----------------------------------------------------------------------------
# FULL NORMALIZATION PIPELINE
# -----------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Full pipeline:
    - Unicode NFC
    - Protect special tags (TP#…)
    - Remove diacritics & tatweel
    - Normalize Arabic letters
    - Normalize digits
    - Remove unwanted characters (#, *, bullets, em dash, -, O, ·, etc.)
    - Clean spacing & noisy lines while preserving headings
    - Restore special tags
    """
    text = unicodedata.normalize("NFC", text)

    text, tag_map = protect_special_tags(text)

    text = remove_diacritics(text)
    text = remove_tatweel(text)
    text = normalize_arabic_letters(text)
    text = normalize_digits(text, DIGIT_TARGET)

    text = UNWANTED_CHARS_RE.sub(" ", text)

    text = clean_structure(text)

    text = restore_special_tags(text, tag_map)

    return text


# -----------------------------------------------------------------------------
# PROCESSING LOOP
# -----------------------------------------------------------------------------

def process_all_texts(base_dir: Path) -> None:
    """
    1. Discover all .txt files.
    2. Match/rename RFP & TP pairs.
    3. Normalize contents and save as UTF-8.
    """
    logger.info("Scanning for text files under: %s", base_dir)
    files = discover_text_files(base_dir)
    logger.info("Found %d text files", len(files))

    logger.info("Classifying files by code...")
    pairs = classify_files(files)
    logger.info("Found %d distinct codes", len(pairs))

    rename_pairs(pairs)

    files = discover_text_files(base_dir)

    for idx, path in enumerate(files, start=1):
        logger.info("(%d/%d) Normalizing: %s", idx, len(files), path)
        text, enc = read_text_with_fallback(path)
        if not enc.lower().startswith("utf-8"):
            logger.info("Converted %s from %s to UTF-8", path, enc)
        cleaned = normalize_text(text)
        write_utf8_text(path, cleaned, base_dir)


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def main() -> None:
    setup_logging(logging.INFO)

    ensure_extracted(ZIP_PATH, EXTRACT_DIR)

    base_dir = BASE_DIR.resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        logger.error("Base directory does not exist or is not a directory: %s", base_dir)
        sys.exit(1)

    logger.info("Starting processing in %s", base_dir)
    logger.info("Digit normalization target: %s", DIGIT_TARGET)
    logger.info("Overwrite in place: %s", OVERWRITE_IN_PLACE)
    logger.info("Dry-run rename: %s", DRY_RUN_RENAME)

    process_all_texts(base_dir)
    logger.info("Done.")


if __name__ == "__main__":
    main()
