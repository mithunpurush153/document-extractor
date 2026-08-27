"""Runtime two-PDF chemical validation.

This module intentionally has no preloaded ASTM reference data.  It accepts
already-extracted ``tables_by_page`` structures for a reference PDF and a
supplier/test PDF, detects the standard/grade, extracts reference requirements
and observed chemistry, and compares them deterministically.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional


ELEMENT_ALIASES = {
    "carbon": ("carbon", "%c", "96c", "$c", "c"),
    "manganese": ("manganese", "%mn", "%6mn", "manganese (mn)", "mn"),
    "phosphorus": ("phosphorus", "phosphor", "%p", "p"),
    "sulfur": ("sulfur", "sulphur", "%s", "96s", "$6s", "s"),
    "silicon": ("silicon", "%si", "96si", "si"),
    "chromium": ("chromium", "%cr", "96cr", "$6cr", "$cr", "cr"),
    "nickel": ("nickel", "ni%", "ni", "nickel (ni)"),
    "molybdenum": ("molybdenum", "molybden", "mo", "mo%"),
    "nitrogen": ("nitrogen", "n%", "n"),
    "titanium": ("titanium", "ti", "ti%"),
    "niobium": ("niobium", "nb", "nb%"),
    "vanadium": ("vanadium", "v", "v%"),
    "copper": ("copper", "cu", "cu%"),
    "cobalt": ("cobalt", "co", "co%"),
    "selenium": ("selenium", "se", "se%"),
}

DISPLAY_NAMES = {
    "carbon": ("Carbon", "%C"),
    "manganese": ("Manganese", "%Mn"),
    "phosphorus": ("Phosphorus", "%P"),
    "sulfur": ("Sulfur", "%S"),
    "silicon": ("Silicon", "%Si"),
    "chromium": ("Chromium", "%Cr"),
    "nickel": ("Nickel", "Ni%"),
    "molybdenum": ("Molybdenum", "Mo"),
    "nitrogen": ("Nitrogen", "N"),
    "titanium": ("Titanium", "Ti%"),
    "niobium": ("Niobium", "Nb%"),
    "vanadium": ("Vanadium", "V%"),
    "copper": ("Copper", "Cu%"),
    "cobalt": ("Cobalt", "Co%"),
    "selenium": ("Selenium", "Se%"),
}

NUMBER_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?")
STANDARD_RE = re.compile(r"\bASTM\s*([A-Z])\s*(\d{3,5})(?:\s*/\s*([A-Z])\s*(\d{3,5}))?", re.I)
GRADE_RE = re.compile(r"\bGRADES?\s*[:\-]?\s*([A-Z0-9][A-Z0-9./_\-]*(?:\s+[A-Z0-9][A-Z0-9./_\-]*){0,2})", re.I)
GRADE_STOP_RE = re.compile(
    r"\b(?:REVI(?:SION)?|REV|DATE|MATERIAL|SPECIFICATION|STANDARD|ROUND|ROUNDBAR|BAR|BARS|SIZE|HEAT|INVOICE|INVOICEL|NO|NUMBER|FOR|PARAMETER|TESTED|CUSTOMER|REQUIREMENT|RESULT|REMARK|CHEMICAL|COMPOSITION|TABLE|PARTICULARS|OBSERVED|SPECIFIED)\b",
    re.I,
)
TYPE_RE = re.compile(
    # A material Type is normally a single designation token (316L, 304L, etc.).
    # Do not greedily consume following OCR words such as "Sample Described".
    r"\bTYPE\s*[:\-]?\s*([A-Z0-9][A-Z0-9./_\-]*)",
    re.I,
)
UNS_RE = re.compile(r"\bUNS\s*[:\-]?\s*([A-Z]\s*\d{4,6})\b", re.I)
DESIGNATION_STOP_RE = re.compile(
    r"\b(?:ANNEALED|ANNEAL|SOLUTION|HEAT|TREAT|TREATED|CONDITION|SIZE|DIAMETER|LENGTH|SPECIFICATION|STANDARD|CERTIFICATE|CERTIFICATION|TEST|REPORT|MATERIAL|GRADE|GRADES|TYPE|SAMPLE|DESCRIBED|BY|CUSTOMER|CUSTOMER'S|AS|FOR|PARAMETER|RESULT|REMARK|CHEMICAL|COMPOSITION|TABLE)\b",
    re.I,
)


def normalize_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = " ".join(text.lower().split())
    return text


def compact(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_text(value))


def standard_key(value: Any) -> Optional[str]:
    text = str(value or "")
    # Prefer an ASTM material-standard expression. Allow OCR variants such as
    # "ASTMA276" as well as "ASTM A276" and ignore the year suffix.
    matches = re.findall(r"\bASTM\s*A\s*(\d{3,5})(?:\s*/\s*A\s*\d{3,5})?", text, flags=re.I)
    if matches:
        # If multiple standards are present, choose the first explicit material
        # standard in this local value; the caller already scopes the search.
        return f"A{matches[0]}"
    match = re.search(r"\bA\s*(\d{3,5})\b", text, re.I)
    return f"A{match.group(1)}" if match else None

def clean_grade(value: Any) -> Optional[str]:
    text = str(value or "")
    if not text:
        return None

    match = GRADE_RE.search(text)
    if not match:
        return None

    grade = re.sub(r"\s+", " ", match.group(1)).strip(" .,:;\t")
    stop = GRADE_STOP_RE.search(grade)
    if stop:
        grade = grade[:stop.start()].strip(" .,:;\t")

    grade = re.sub(
        r"\s+(?:REVI(?:SION)?|REV|DATE|MATERIAL|BAR|BARS|SIZE|HEAT|INVOICE|NO)\b.*$",
        "",
        grade,
        flags=re.I,
    ).strip(" .,:;-_")
    return grade or None


def _clean_designation(raw: str) -> Optional[str]:
    value = re.sub(r"\s+", " ", raw or "").strip(" .,:;-_")
    stop = DESIGNATION_STOP_RE.search(value)
    if stop:
        value = value[:stop.start()].strip(" .,:;-_")
    return value or None


def extract_material_designation(value: Any) -> Optional[str]:
    """Extract only the material designation from one local ASTM phrase.

    The parser first finds the full ASTM phrase, then filters only the useful
    designation token(s). Extra OCR words are deliberately ignored.

    Examples:
      ASTM A479:2024 TYPE 316L -> 316L
      ASTM A276 - UNS S32760 (ANNEALED) -> S32760
      ASTM A182/A182-24a Grade F XM-19 -> F XM-19
      ASTM A194/A194M GRADE 8M FOR ... -> 8M
    """
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return None

    m = re.search(
        r"\bASTM\s*A\s*\d{3,5}(?:\s*/\s*A\s*\d{3,5})?[^.!?;]{0,180}",
        text, flags=re.I,
    )
    local = m.group(0).strip() if m else text

    # TYPE is intentionally single-token: "TYPE 316L Sample Described" must
    # produce only 316L.
    type_match = TYPE_RE.search(local)
    if type_match:
        return type_match.group(1).strip(" .,:;-_").upper()

    uns_match = UNS_RE.search(local)
    if uns_match:
        return "".join(uns_match.group(1).upper().split())

    # GRADE may legitimately contain multiple tokens, e.g. "F XM-19".
    grade_match = re.search(
        r"\bGRADES?\s*[:\-]?\s*(.*?)\s*(?=\b(?:FOR|SAMPLE|DESCRIBED|BY|CUSTOMER|CUSTOMER'S|MATERIAL|SPECIFICATION|STANDARD|TEST|REPORT|RESULT|REMARK|CHEMICAL|COMPOSITION|TABLE|REVI(?:SION)?|REV|DATE|SIZE|HEAT|INVOICE|NO)\b|$)",
        local, flags=re.I,
    )
    if grade_match:
        grade = re.sub(r"\s+", " ", grade_match.group(1)).strip(" .,:;-_")
        if grade:
            return grade.upper()

    # Standalone field/cell fallbacks.
    type_match = TYPE_RE.search(text)
    if type_match:
        return type_match.group(1).strip(" .,:;-_").upper()
    uns_match = UNS_RE.search(text)
    if uns_match:
        return "".join(uns_match.group(1).upper().split())
    grade_match = re.search(
        r"\bGRADES?\s*[:\-]?\s*(.*?)\s*(?=\b(?:FOR|SAMPLE|DESCRIBED|BY|CUSTOMER|CUSTOMER'S|MATERIAL|SPECIFICATION|STANDARD|TEST|REPORT|RESULT|REMARK|CHEMICAL|COMPOSITION|TABLE|REVI(?:SION)?|REV|DATE|SIZE|HEAT|INVOICE|NO)\b|$)",
        text, flags=re.I,
    )
    if grade_match:
        grade = re.sub(r"\s+", " ", grade_match.group(1)).strip(" .,:;-_")
        if grade:
            return grade.upper()
    return None

def grade_from_table_metadata(tables: Dict[str, Any]) -> Optional[str]:
    """Prefer explicit Grade/Type/UNS metadata from extracted tables."""
    for page_tables in tables.values():
        if not isinstance(page_tables, list):
            continue
        for table in page_tables:
            if not isinstance(table, dict):
                continue
            for col in table.get("columns", []) or []:
                col_text = str(col or "").strip()
                candidate = extract_material_designation(col_text)
                if candidate:
                    return candidate
            for row in table.get("data", []) or []:
                if not isinstance(row, dict):
                    continue
                for key, value in row.items():
                    key_norm = normalize_text(key)
                    raw = str(value or "").strip()
                    if ("grade" in key_norm or "type" in key_norm or "uns" in key_norm or
                        "material standard" in key_norm or key_norm in {"standard", "specification"}):
                        candidate = extract_material_designation(raw) or extract_material_designation(str(key))
                        if candidate and candidate.lower() not in {"grade", "grades", "type", "uns"}:
                            return candidate.strip(" .,:;-_")
    return None


def grade_matches(target: str, candidate: str) -> bool:
    t = compact(target)
    c = compact(candidate)
    if not t or not c:
        return False
    if t == c or t in c or c in t:
        return True
    # For values such as "F XM-19" vs "XM-19", compare meaningful tokens.
    t_tokens = [x for x in re.split(r"[^a-z0-9]+", normalize_text(target)) if len(x) >= 2]
    c_tokens = [x for x in re.split(r"[^a-z0-9]+", normalize_text(candidate)) if len(x) >= 2]
    return any(tok in c_tokens for tok in t_tokens)


def iter_table_strings(tables: Dict[str, Any]) -> Iterable[str]:
    for page_tables in tables.values():
        if not isinstance(page_tables, list):
            continue
        for table in page_tables:
            if not isinstance(table, dict):
                continue
            for col in table.get("columns", []) or []:
                yield str(col)
            for row in table.get("data", []) or []:
                if isinstance(row, dict):
                    # Keys matter too: some table extractors keep semantic
                    # labels such as "Standard" / "Grade" as column names.
                    for key, value in row.items():
                        if key not in (None, ""):
                            yield str(key)
                        if value not in (None, ""):
                            yield str(value)


def identify_standard_and_grade(
    tables: Dict[str, Any],
    document_text: str = "",
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Identify the material standard and designation from a local ASTM phrase.

    The first choice is a complete ASTM phrase in the document text, e.g.
    ``ASTM A479:2024 TYPE 316L``. We extract the standard and then only the
    designation (grade/type/UNS) from that same local phrase. This avoids
    accidentally combining unrelated words elsewhere in a long PDF.
    """
    standard = None
    designation = None
    standard_text = None
    designation_text = None

    if document_text:
        text = re.sub(r"\s+", " ", str(document_text or "")).strip()
        m = re.search(
            r"\bASTM\s*A\s*\d{3,5}(?:\s*/\s*A\s*\d{3,5})?[^.!?;]{0,180}",
            text,
            flags=re.I,
        )
        if m:
            local = m.group(0).strip()
            standard = standard_key(local)
            if standard:
                standard_text = local
                designation = extract_material_designation(local)
                designation_text = local

        # If no explicit ASTM phrase was captured, use the whole text only as
        # a fallback for standard detection, then inspect nearby table metadata.
        if standard is None:
            standard = standard_key(text)
            if standard:
                standard_text = text[:500]

    # Table metadata is the next fallback. Prefer explicit fields rather than
    # arbitrary cells so unrelated ASTM references don't become the designation.
    if standard is None or designation is None:
        for page_tables in tables.values():
            if not isinstance(page_tables, list):
                continue
            for table in page_tables:
                if not isinstance(table, dict):
                    continue
                for row in table.get("data", []) or []:
                    if not isinstance(row, dict):
                        continue
                    for key, value in row.items():
                        key_norm = normalize_text(key)
                        raw = str(value or "").strip()
                        if standard is None and (
                            "material standard" in key_norm or key_norm in {"standard", "specification"}
                        ):
                            candidate = standard_key(raw)
                            if candidate:
                                standard = candidate
                                standard_text = raw
                        if designation is None and any(token in key_norm for token in ("grade", "type", "uns", "designation")):
                            candidate = extract_material_designation(raw) or extract_material_designation(str(key))
                            if candidate:
                                designation = candidate
                                designation_text = raw or str(key)
                if standard and designation:
                    break
            if standard and designation:
                break

    # Last fallback: a local table/cell containing a full ASTM phrase.
    if standard is None or designation is None:
        for value in iter_table_strings(tables):
            value_text = str(value or "")
            if standard is None:
                candidate = standard_key(value_text)
                if candidate:
                    standard = candidate
                    standard_text = value_text
            if designation is None:
                candidate = extract_material_designation(value_text)
                if candidate:
                    designation = candidate
                    designation_text = value_text
            if standard and designation:
                break

    return standard, designation, standard_text, designation_text


def table_matrix(table: Dict[str, Any]) -> list[list[str]]:
    columns = list(table.get("columns", []) or [])
    rows = table.get("data", []) or []

    meaningful_columns = bool(columns) and not all(str(c).strip().lower().startswith("col_") for c in columns)
    matrix: list[list[str]] = []
    if meaningful_columns:
        matrix.append([str(c or "") for c in columns])

    for row in rows:
        if isinstance(row, dict):
            # Preserve the table's column order; unknown keys go afterward.
            ordered = []
            seen = set()
            for c in columns:
                ordered.append(str(row.get(c, "") or ""))
                seen.add(c)
            for k, v in row.items():
                if k not in seen:
                    ordered.append(str(v or ""))
            matrix.append(ordered)
    return matrix


def find_element_in_cell(value: Any) -> Optional[str]:
    text = normalize_text(value)
    if not text:
        return None

    # First prefer exact aliases. This is important for OCR strings such as
    # "96S" and "96Si" where a short alias like "96s" is a substring of
    # the longer silicon token.
    exact = []
    for element, aliases in ELEMENT_ALIASES.items():
        for alias in aliases:
            a = normalize_text(alias)
            if text == a:
                exact.append((len(a), element))
    if exact:
        exact.sort(reverse=True)
        return exact[0][1]

    # Then allow descriptive names inside richer cells such as
    # "Carbon (C) %" or "Specification: Chromium (Cr)". Avoid short-symbol
    # substring matches because they are too ambiguous.
    for element, aliases in sorted(ELEMENT_ALIASES.items(), key=lambda item: max(map(len, item[1])), reverse=True):
        for alias in aliases:
            a = normalize_text(alias)
            if len(a) >= 4 and a in text:
                return element
    return None


def numeric_value(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    match = NUMBER_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def parse_requirement(value: Any) -> Optional[dict[str, Any]]:
    text = normalize_text(value)
    if not text or text in {".", "...", "-", "na", "n/a"}:
        return None
    # Reference limits are non-negative in the material tables.  Do not treat
    # the dash in a range (16.0-18.0) as a negative sign.
    nums = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", text)]
    if not nums:
        return None

    if "max" in text and "min" not in text:
        return {"type": "MAX", "max": nums[0], "text": f"<= {nums[0]:g}"}
    if "min" in text and "max" not in text:
        return {"type": "MIN", "min": nums[0], "text": f">= {nums[0]:g}"}
    # Only treat two values as a range when the source cell explicitly expresses
    # a range. This prevents OCR from combining adjacent columns (for example
    # Carbon=0.03 and Manganese=2.00) and incorrectly turning them into 0.03-2.
    if len(nums) >= 2 and ("-" in text or re.search(r"\bto\b", text)):
        lo, hi = nums[0], nums[1]
        return {"type": "RANGE", "min": lo, "max": hi, "text": f"{lo:g} - {hi:g}"}
    if len(nums) >= 2:
        return None
    # ASTM chemical tables commonly state a single number with a footnote
    # meaning maximum unless otherwise indicated. This is the convention used
    # by A276/A479-style reference tables.
    if len(nums) == 1:
        return {"type": "MAX", "max": nums[0], "text": f"<= {nums[0]:g}"}
    return None


def find_header_row(matrix: list[list[str]]) -> Optional[int]:
    best = None
    best_score = 0
    for idx, row in enumerate(matrix[:8]):
        score = len({e for e in (find_element_in_cell(v) for v in row) if e})
        if score > best_score:
            best = idx
            best_score = score
    return best if best_score >= 3 else None



def _ocr_word_box(item: Dict[str, Any]) -> Optional[tuple[float, float, float, float, str]]:
    """Return x1,y1,x2,y2,text from one raw OCR detection."""
    try:
        text = str(item.get("text", "") or "").strip()
        bbox = item.get("bbox") or []
        if not text or len(bbox) < 2:
            return None
        xs = [float(p[0]) for p in bbox if isinstance(p, (list, tuple)) and len(p) >= 2]
        ys = [float(p[1]) for p in bbox if isinstance(p, (list, tuple)) and len(p) >= 2]
        if not xs or not ys:
            return None
        return min(xs), min(ys), max(xs), max(ys), text
    except (TypeError, ValueError):
        return None


def _ocr_lines(page_detections: list[dict[str, Any]], y_tol: float = 18.0) -> list[list[dict[str, Any]]]:
    """Cluster DocTR word detections into approximate text lines by y-center."""
    words = []
    for item in page_detections or []:
        box = _ocr_word_box(item)
        if not box:
            continue
        x1, y1, x2, y2, text = box
        words.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "xc": (x1 + x2) / 2.0, "yc": (y1 + y2) / 2.0, "text": text,
        })
    words.sort(key=lambda w: (w["yc"], w["xc"]))
    lines: list[dict[str, Any]] = []
    for word in words:
        best = None
        best_delta = None
        for line in lines[-8:]:
            delta = abs(word["yc"] - line["yc"])
            if delta <= y_tol and (best_delta is None or delta < best_delta):
                best = line
                best_delta = delta
        if best is None:
            lines.append({"yc": word["yc"], "words": [word]})
        else:
            best["words"].append(word)
            best["yc"] = sum(w["yc"] for w in best["words"]) / len(best["words"])
    return [sorted(line["words"], key=lambda w: w["xc"]) for line in lines]


def _line_text(line: list[dict[str, Any]]) -> str:
    return " ".join(w["text"] for w in line)


def _designation_token_matches(target: str, candidate: str) -> bool:
    """Match a material designation while tolerating OCR footnote marks."""
    t = compact(target)
    c = compact(candidate)
    if not t or not c:
        return False
    if t == c:
        return True
    # ASTM reference tables frequently put a superscript footnote directly
    # after the designation (e.g. S32760a, S327605). Keep only a tiny suffix.
    if c.startswith(t) and len(c) - len(t) <= 2:
        return True
    return False


def _parse_reference_cell(value: Any) -> Optional[dict[str, Any]]:
    """Parse a reference-table cell with ASTM's default-max convention.

    Many ASTM chemical tables state in a footnote that a single number is a
    maximum unless a range or minimum is explicitly indicated. The existing
    generic parser intentionally does not assume that convention. The
    chemistry-specific OCR parser can safely apply it after the target row and
    element column are known.
    """
    parsed = parse_requirement(value)
    if parsed is not None:
        return parsed
    text = normalize_text(value)
    if not text or text in {".", "..", "...", "-", "na", "n/a"}:
        return None
    nums = re.findall(r"\d+(?:[.,]\d+)?", text)
    if len(nums) == 1:
        try:
            number = float(nums[0].replace(",", "."))
        except ValueError:
            return None
        return {"type": "MAX", "max": number, "text": f"<= {number:g}"}
    return None


def _reference_requirements_from_ocr(
    reference_ocr: Dict[str, Any], target_grade: str,
) -> Optional[dict[str, dict[str, Any]]]:
    """Reference-table extractor driven by DocTR word coordinates.

    This intentionally does not depend on ``table_extractor.py``. ASTM
    reference tables often repeat headers on continuation pages and use
    multi-line/hyphenated column headings, so we locate the chemical-table
    header by its element names and then read the target material row by X
    position.
    """
    if not reference_ocr or not target_grade:
        return None

    header_aliases = {
        "carbon": ("carbon",),
        "manganese": ("manganese",),
        "phosphorus": ("phosphorus", "phosphor"),
        "sulfur": ("sulfur", "sulphur"),
        "silicon": ("silicon",),
        "chromium": ("chromium",),
        "nickel": ("nickel",),
        "nitrogen": ("nitrogen",),
        "molybdenum": ("molybdenum", "molybden", "molyb"),
        "titanium": ("titanium",),
        "niobium": ("niobium",),
        "vanadium": ("vanadium",),
        "copper": ("copper",),
        "cobalt": ("cobalt",),
        "selenium": ("selenium",),
    }

    def collapsed_word_text(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", normalize_text(value))

    def header_anchors_from_lines(lines: list[list[dict[str, Any]]], start_idx: int) -> dict[str, float]:
        # Look only in a compact header window. This avoids body-row words
        # creating false element anchors.
        words = []
        for line in lines[start_idx:min(len(lines), start_idx + 12)]:
            words.extend(line)
        if not words:
            return {}

        words.sort(key=lambda w: (w["xc"], w["yc"]))
        clusters: list[list[dict[str, Any]]] = []
        x_tol = 38.0
        for w in words:
            best_idx = None
            best_delta = None
            for idx, cluster in enumerate(clusters):
                center = sum(item["xc"] for item in cluster) / len(cluster)
                delta = abs(w["xc"] - center)
                if delta <= x_tol and (best_delta is None or delta < best_delta):
                    best_idx = idx
                    best_delta = delta
            if best_idx is None:
                clusters.append([w])
            else:
                clusters[best_idx].append(w)

        anchors: dict[str, float] = {}
        for cluster in clusters:
            cluster_sorted = sorted(cluster, key=lambda w: w["yc"])
            collapsed = "".join(collapsed_word_text(w["text"]) for w in cluster_sorted)
            if not collapsed:
                continue
            for element, aliases in header_aliases.items():
                if element in anchors:
                    continue
                for alias in aliases:
                    if collapsed == alias or alias in collapsed:
                        # Use the median X position of the words in this header
                        # cluster. This is more stable than taking the first word.
                        xs = sorted(w["xc"] for w in cluster_sorted)
                        anchors[element] = xs[len(xs) // 2]
                        break
        return anchors

    for _page_key, detections in reference_ocr.items():
        if not isinstance(detections, list) or len(detections) < 8:
            continue
        lines = _ocr_lines(detections)
        if len(lines) < 6:
            continue

        # Find a chemical-table marker on this page. Continuation pages such as
        # "TABLE 1 Continued" often omit the word "Chemical", so also accept a
        # nearby element-rich header as evidence of the same table.
        marker_idxs = []
        for i, line in enumerate(lines):
            t = normalize_text(_line_text(line))
            if "chemical composition" in t or "chemical requirements" in t or "table 1" in t:
                marker_idxs.append(i)

        header_candidates = []
        search_starts = marker_idxs or list(range(min(len(lines), 30)))
        for start_idx in search_starts:
            for idx in range(start_idx, min(len(lines), start_idx + 12)):
                anchors = header_anchors_from_lines(lines, idx)
                if len(anchors) >= 6:
                    header_candidates.append((len(anchors), idx, anchors))

        if not header_candidates:
            continue
        _, header_idx, anchors = max(header_candidates, key=lambda item: item[0])

        target_compact = compact(target_grade)
        target_line_idx = None
        target_word = None
        for i in range(header_idx + 1, min(len(lines), header_idx + 70)):
            for w in lines[i]:
                if _designation_token_matches(target_compact, w["text"]):
                    target_line_idx = i
                    target_word = w
                    break
            if target_line_idx is not None:
                break
        if target_line_idx is None:
            continue

        # Keep the actual row only. ASTM rows are normally aligned on one OCR
        # line; using adjacent lines risks taking numbers from the next grade.
        yc = target_word["yc"]
        row_words = [w for w in lines[target_line_idx] if abs(w["yc"] - yc) <= 24]
        if not row_words:
            continue

        ordered_anchors = sorted(anchors.items(), key=lambda kv: kv[1])
        x_centers = [x for _, x in ordered_anchors]
        requirements: dict[str, dict[str, Any]] = {}

        # Add a left-side boundary between the target designation column and the
        # first chemistry column. This is critical when the first numeric value
        # is Carbon and the target token is in the same row.
        first_x = x_centers[0]
        left_boundary = (target_word["xc"] + first_x) / 2.0

        for pos, (element, x) in enumerate(ordered_anchors):
            if pos == 0:
                left = left_boundary
            else:
                left = (x_centers[pos - 1] + x) / 2.0
            right = (x + x_centers[pos + 1]) / 2.0 if pos + 1 < len(x_centers) else x + 55.0
            cell_words = [w for w in row_words if left <= w["xc"] < right]
            cell_text = " ".join(w["text"] for w in sorted(cell_words, key=lambda w: w["xc"]))
            parsed = _parse_reference_cell(cell_text)
            if parsed:
                requirements[element] = parsed

        if len(requirements) >= 5:
            return requirements

    return None


def extract_reference_requirements(tables: Dict[str, Any], target_grade: str) -> dict[str, dict[str, Any]]:
    # Horizontal ASTM table: grade is a row; elements are columns.
    for page_tables in tables.values():
        for table in page_tables if isinstance(page_tables, list) else []:
            matrix = table_matrix(table)
            if not matrix:
                continue
            header_idx = find_header_row(matrix)
            if header_idx is not None:
                header = matrix[header_idx]
                element_cols = {element: idx for idx, cell in enumerate(header) if (element := find_element_in_cell(cell))}
                if len(element_cols) >= 3:
                    for row in matrix[header_idx + 1:]:
                        row_text = " ".join(row)
                        # Limit grade matching to cells near the left side to reduce false matches.
                        candidate_cells = row[: min(3, len(row))]
                        if any(grade_matches(target_grade, c) for c in candidate_cells):
                            requirements: dict[str, dict[str, Any]] = {}
                            for element, col_idx in element_cols.items():
                                if col_idx < len(row):
                                    parsed = parse_requirement(row[col_idx])
                                    if parsed:
                                        requirements[element] = parsed
                            if requirements:
                                return requirements

    # Vertical table: grade is a column; elements are rows.
    for page_tables in tables.values():
        for table in page_tables if isinstance(page_tables, list) else []:
            matrix = table_matrix(table)
            if len(matrix) < 3:
                continue
            header_idx = 0
            grade_col = None
            for idx, cell in enumerate(matrix[header_idx]):
                if grade_matches(target_grade, cell):
                    grade_col = idx
                    break
            if grade_col is None:
                for idx, row in enumerate(matrix[:6]):
                    for col_idx, cell in enumerate(row):
                        if grade_matches(target_grade, cell):
                            grade_col = col_idx
                            header_idx = idx
                            break
                    if grade_col is not None:
                        break
            if grade_col is None:
                continue
            requirements = {}
            for row in matrix[header_idx + 1:]:
                if not row:
                    continue
                element = find_element_in_cell(row[0])
                if not element and len(row) > 1:
                    element = find_element_in_cell(" ".join(row[:2]))
                if element and grade_col < len(row):
                    parsed = parse_requirement(row[grade_col])
                    if parsed:
                        requirements[element] = parsed
            if len(requirements) >= 3:
                return requirements

    raise ValueError(f"Could not find a chemical requirements row for grade '{target_grade}' in the uploaded reference PDF")


def extract_observed_composition(tables: Dict[str, Any]) -> dict[str, float]:
    observed: dict[str, float] = {}

    # Row-based laboratory "Chemical Analysis" table.
    # Example layout:
    #   Element | Result | R/V | Test Method
    # The result is selected from the dedicated Result column when available,
    # otherwise from the first numeric field on the element row.
    for page_tables in tables.values():
        for table in page_tables if isinstance(page_tables, list) else []:
            matrix = table_matrix(table)
            if len(matrix) < 2:
                continue

            normalized_rows = [[normalize_text(x) for x in row] for row in matrix]
            full_text = normalize_text(" ".join(" ".join(row) for row in matrix))
            if "chemical analysis" not in full_text:
                continue

            result_col = None
            element_col = None
            header_idx = None
            for r_idx, row in enumerate(normalized_rows[:6]):
                result_candidates = [i for i, x in enumerate(row) if x == "result" or "result" in x]
                element_candidates = [i for i, x in enumerate(row) if "element" in x or "chemical analysis" in x]
                if result_candidates:
                    result_col = result_candidates[0]
                    if element_candidates:
                        element_col = element_candidates[0]
                    header_idx = r_idx
                    break

            local: dict[str, float] = {}
            for r_idx, row in enumerate(matrix):
                if header_idx is not None and r_idx <= header_idx:
                    continue

                # Identify an element anywhere in the row, but prefer the first
                # cell(s), which is where these lab reports place the element name.
                element = None
                element_idx = None
                for idx, cell in enumerate(row):
                    candidate = find_element_in_cell(cell)
                    if candidate:
                        element = candidate
                        element_idx = idx
                        break
                if not element:
                    continue

                value = None
                if result_col is not None and result_col < len(row):
                    value = numeric_value(row[result_col])

                # Fallback: choose the first numeric value after the element cell.
                if value is None:
                    start_idx = (element_idx + 1) if element_idx is not None else 0
                    for cell in row[start_idx:]:
                        candidate_value = numeric_value(cell)
                        if candidate_value is not None:
                            value = candidate_value
                            break

                if value is not None:
                    local[element] = value

            if len(local) >= 3:
                observed.update(local)

    if observed:
        return observed

    # Vertical supplier report: Element | Specification | Result/Observed.
    for page_tables in tables.values():
        for table in page_tables if isinstance(page_tables, list) else []:
            matrix = table_matrix(table)
            if len(matrix) < 3:
                continue
            header_idx = None
            element_col = result_col = None
            for r_idx, row in enumerate(matrix[:5]):
                low = [normalize_text(x) for x in row]
                if any("element" in x for x in low) and any(("result" in x or "observed" in x) for x in low):
                    header_idx = r_idx
                    element_col = next(i for i, x in enumerate(low) if "element" in x)
                    result_col = next(i for i, x in enumerate(low) if "result" in x or "observed" in x)
                    break
            if header_idx is not None:
                local = {}
                for row in matrix[header_idx + 1:]:
                    if element_col >= len(row) or result_col >= len(row):
                        continue
                    element = find_element_in_cell(row[element_col])
                    value = numeric_value(row[result_col])
                    if element and value is not None:
                        local[element] = value
                if len(local) >= 3:
                    observed.update(local)

    if observed:
        return observed

    # Horizontal supplier table: element symbols are header cells and an observed/result row follows.
    for page_tables in tables.values():
        for table in page_tables if isinstance(page_tables, list) else []:
            matrix = table_matrix(table)
            header_idx = find_header_row(matrix)
            if header_idx is None:
                continue
            header = matrix[header_idx]
            element_cols = {element: idx for idx, cell in enumerate(header) if (element := find_element_in_cell(cell))}
            if len(element_cols) < 3:
                continue
            candidates = matrix[header_idx + 1:]
            chosen = None
            best_numeric = -1
            for row in candidates:
                row_text = normalize_text(" ".join(row))
                nums = sum(1 for idx in element_cols.values() if idx < len(row) and numeric_value(row[idx]) is not None)
                if "observed" in row_text or "analysis" in row_text or "result" in row_text or nums > best_numeric:
                    chosen = row
                    best_numeric = nums
                if "observed" in row_text and nums >= 3:
                    break
            if chosen is not None:
                local = {}
                for element, idx in element_cols.items():
                    if idx < len(chosen):
                        value = numeric_value(chosen[idx])
                        if value is not None:
                            local[element] = value
                if len(local) >= 3:
                    observed.update(local)
    return observed



def extract_observed_composition_from_ocr(reference_ocr: Optional[Dict[str, Any]], target_text: str = "") -> dict[str, float]:
    """Extract supplier chemistry directly from DocTR OCR lines.

    This is a fallback for scanned lab reports where the generic table extractor
    cannot reconstruct the table. It looks for a 'Chemical Analysis'/'Chemical
    Composition' section, finds element-named rows, and takes the first numeric
    value to the right of the element name as the observed result. Limits and
    test-method numbers that occur later on the row are ignored.
    """
    observed: dict[str, float] = {}
    if not reference_ocr:
        return observed

    for _page_key, detections in reference_ocr.items():
        if not isinstance(detections, list):
            continue
        lines = _ocr_lines(detections)
        if not lines:
            continue

        chem_idx = None
        for i, line in enumerate(lines):
            t = normalize_text(_line_text(line))
            if "chemical analysis" in t or "chemical composition" in t:
                chem_idx = i
                break
        if chem_idx is None:
            continue

        # Scan the chemistry section, allowing OCR to split a row across up to
        # two adjacent lines.
        for i in range(chem_idx + 1, min(len(lines), chem_idx + 80)):
            line = lines[i]
            line_text = _line_text(line)
            element = None
            element_x = None
            for w in line:
                candidate = find_element_in_cell(w["text"])
                if candidate:
                    element = candidate
                    element_x = w["x2"]
                    break
            if not element:
                continue

            numeric_tokens = []
            for w in line:
                if element_x is not None and w["xc"] <= element_x:
                    continue
                for match in re.findall(r"\d+(?:[.,]\d+)?", w["text"]):
                    try:
                        numeric_tokens.append(float(match.replace(",", ".")))
                    except ValueError:
                        pass

            # If the value wrapped to the next OCR line, look one line ahead
            # when the next line is close vertically and contains numbers.
            if not numeric_tokens and i + 1 < len(lines):
                next_line = lines[i + 1]
                if abs(next_line[0]["yc"] - line[0]["yc"]) <= 45:
                    for w in next_line:
                        for match in re.findall(r"\d+(?:[.,]\d+)?", w["text"]):
                            try:
                                numeric_tokens.append(float(match.replace(",", ".")))
                            except ValueError:
                                pass

            if numeric_tokens:
                observed[element] = numeric_tokens[0]

        if len(observed) >= 3:
            return observed

    return observed

def compare(reference_requirements: dict[str, dict[str, Any]], observed: dict[str, float]) -> dict[str, Any]:
    elements = []
    for element, req in reference_requirements.items():
        value = observed.get(element)
        name, symbol = DISPLAY_NAMES.get(element, (element.title(), element))
        status = "NOT_REPORTED"
        if value is not None:
            if req["type"] == "MAX":
                status = "PASS" if value <= req["max"] else "FAIL"
            elif req["type"] == "MIN":
                status = "PASS" if value >= req["min"] else "FAIL"
            elif req["type"] == "RANGE":
                status = "PASS" if req["min"] <= value <= req["max"] else "FAIL"
        elements.append({
            "element": name,
            "symbol": symbol,
            "observed": value,
            "requirement_text": req["text"],
            "status": status,
        })

    summary = {
        "total": len(elements),
        "pass": sum(e["status"] == "PASS" for e in elements),
        "fail": sum(e["status"] == "FAIL" for e in elements),
        "not_reported": sum(e["status"] == "NOT_REPORTED" for e in elements),
    }
    return {
        "elements": elements,
        "summary": summary,
        "overall_status": "FAIL" if summary["fail"] else "PASS",
    }


def validate_two_documents(
    reference_tables: Dict[str, Any],
    test_tables: Dict[str, Any],
    reference_text: str = "",
    test_text: str = "",
    reference_ocr: Optional[Dict[str, Any]] = None,
    test_ocr: Optional[Dict[str, Any]] = None,
) -> dict[str, Any]:
    ref_standard, _, ref_standard_text, _ = identify_standard_and_grade(reference_tables, reference_text)
    test_standard, test_grade, test_standard_text, test_grade_text = identify_standard_and_grade(test_tables, test_text)

    if not test_standard or not test_grade:
        raise ValueError("Could not identify the ASTM standard and grade from the test report PDF")
    if not ref_standard:
        raise ValueError("Could not identify the ASTM standard from the reference PDF")
    if ref_standard != test_standard:
        raise ValueError(
            f"Standard mismatch: reference PDF is {ref_standard}, test report is {test_standard}"
        )

    # Reference standards are often scanned/multi-column ASTM tables. Prefer the
    # raw DocTR OCR+bounding-box parser first because the generic table extractor
    # can merge adjacent numeric columns and produce a plausible-looking but wrong
    # requirement (for example Carbon=0.03 2.00). If OCR cannot reconstruct the
    # target row, fall back to the generic table structure.
    requirements = _reference_requirements_from_ocr(reference_ocr or {}, test_grade)
    if not requirements:
        requirements = extract_reference_requirements(reference_tables, test_grade)

    if not requirements:
        raise ValueError(f"Could not find a chemical requirements row for grade '{test_grade}' in the uploaded reference PDF")

    observed = extract_observed_composition(test_tables)
    if not observed:
        observed = extract_observed_composition_from_ocr(test_ocr or {}, test_text)
    if not observed:
        raise ValueError("Could not extract a chemical composition table from the test report PDF")

    validation = compare(requirements, observed)
    return {
        "reference_document": {"standard": ref_standard, "source_text": ref_standard_text},
        "test_document": {
            "standard": test_standard, "grade": test_grade,
            "standard_text": test_standard_text, "grade_text": test_grade_text,
        },
        "standard": test_standard, "grade": test_grade,
        "reference_requirements": requirements,
        "observed_composition": observed,
        "validation_result": validation,
        "error": None,
    }