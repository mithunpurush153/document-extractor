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


def normalize_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = " ".join(text.lower().split())
    return text


def compact(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_text(value))


def standard_key(value: Any) -> Optional[str]:
    text = str(value or "")
    # Prefer ASTM Axxxx references and, when a whole document contains several
    # ASTM references, choose the A-standard that occurs most often. This avoids
    # mistaking a referenced test method (for example ASTM A370) for the document
    # material standard.
    matches = re.findall(r"\bASTM\s+A\s*(\d{3,5})\b", text, flags=re.I)
    if matches:
        counts = {}
        for number in matches:
            key = f"A{number}"
            counts[key] = counts.get(key, 0) + 1
        return max(counts, key=lambda k: counts[k])
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


def grade_from_table_metadata(tables: Dict[str, Any]) -> Optional[str]:
    """Prefer explicit Grade/Grades metadata before using full OCR text."""
    for page_tables in tables.values():
        if not isinstance(page_tables, list):
            continue
        for table in page_tables:
            if not isinstance(table, dict):
                continue
            for col in table.get("columns", []) or []:
                col_text = str(col or "").strip()
                if re.search(r"\bGRADES?\b", col_text, flags=re.I):
                    candidate = clean_grade(col_text)
                    if candidate:
                        return candidate
            for row in table.get("data", []) or []:
                if not isinstance(row, dict):
                    continue
                for key, value in row.items():
                    key_norm = normalize_text(key)
                    if re.search(r"\bgrade\b", key_norm):
                        raw = str(value or "").strip()
                        candidate = clean_grade(raw) or raw
                        if candidate and candidate.lower() not in {"grade", "grades"}:
                            return candidate.strip(" .,:;-_")
                    if "material standard" in key_norm:
                        candidate = clean_grade(value)
                        if candidate:
                            return candidate
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
    standard = None
    grade = grade_from_table_metadata(tables)
    standard_text = None
    grade_text = grade if grade else None

    # Prefer an explicit material-standard field from extracted tables.
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
                    if standard is None and (
                        "material standard" in key_norm
                        or key_norm in {"standard", "specification"}
                    ):
                        candidate = standard_key(value)
                        if candidate:
                            standard = candidate
                            standard_text = str(value).strip()
                    if grade is None and "grade" in key_norm:
                        raw = str(value or "").strip()
                        candidate = clean_grade(raw) or raw
                        if candidate and candidate.lower() not in {"grade", "grades"}:
                            grade = candidate.strip(" .,:;-_")
                            grade_text = grade

    # OCR text is a fallback only. This avoids capturing neighboring table labels
    # such as "8M REVI DATE BARS SIZE" as one grade string.
    if document_text:
        if standard is None:
            material_match = re.search(
                r"(?:material\s+standard\s+specification|material\s+standard|specification)\s*[:\-]?\s*([^\n]{0,160})",
                document_text, flags=re.I,
            )
            if material_match:
                candidate = standard_key(material_match.group(1))
                if candidate:
                    standard = candidate
                    standard_text = material_match.group(1).strip()
        if standard is None:
            candidate = standard_key(document_text)
            if candidate:
                standard = candidate
                standard_text = document_text.strip()
        if grade is None:
            candidate = clean_grade(document_text)
            if candidate:
                grade = candidate
                grade_text = document_text.strip()

    # Last fallback: individual table cells/column names.
    if standard is None or grade is None:
        for value in iter_table_strings(tables):
            if standard is None:
                candidate = standard_key(value)
                if candidate:
                    standard = candidate
                    standard_text = str(value).strip()
            if grade is None:
                candidate = clean_grade(value)
                if candidate:
                    grade = candidate
                    grade_text = str(value).strip()
            if standard and grade:
                break

    return standard, grade, standard_text, grade_text


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
    if len(nums) >= 2 and "-" in text:
        lo, hi = nums[0], nums[1]
        return {"type": "RANGE", "min": lo, "max": hi, "text": f"{lo:g} - {hi:g}"}
    if len(nums) >= 2:
        lo, hi = nums[0], nums[1]
        return {"type": "RANGE", "min": lo, "max": hi, "text": f"{lo:g} - {hi:g}"}
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


def _reference_requirements_from_ocr(
    reference_ocr: Dict[str, Any], target_grade: str,
) -> Optional[dict[str, dict[str, Any]]]:
    """Fallback parser for scanned ASTM reference tables using DocTR bboxes."""
    if not reference_ocr or not target_grade:
        return None

    header_aliases = {
        "carbon": ("carbon",), "manganese": ("manganese",),
        "phosphorus": ("phosphorus", "phosphor"), "sulfur": ("sulfur", "sulphur"),
        "silicon": ("silicon",), "chromium": ("chromium",), "nickel": ("nickel",),
        "molybdenum": ("molybdenum", "molybden", "molyb"), "nitrogen": ("nitrogen",),
        "titanium": ("titanium",), "niobium": ("niobium",), "vanadium": ("vanadium",),
        "copper": ("copper",), "cobalt": ("cobalt",), "selenium": ("selenium",),
    }

    def header_element(text: str) -> Optional[str]:
        n = normalize_text(text).replace(",", "").replace("%", " ")
        for element, aliases in header_aliases.items():
            if any(re.search(rf"\b{re.escape(alias)}\b", n) for alias in aliases):
                return element
        return None

    for _page_key, detections in reference_ocr.items():
        if not isinstance(detections, list):
            continue
        lines = _ocr_lines(detections)
        if len(lines) < 6:
            continue

        chem_idx = None
        for i, line in enumerate(lines):
            t = normalize_text(_line_text(line))
            if "chemical composition" in t or "chemical requirements" in t:
                chem_idx = i
                break
        if chem_idx is None:
            for i, line in enumerate(lines):
                t = normalize_text(_line_text(line))
                nearby = " ".join(_line_text(lines[j]) for j in range(i, min(len(lines), i + 4)))
                if "table 1" in t and "chemical" in normalize_text(nearby):
                    chem_idx = i
                    break
        if chem_idx is None:
            continue

        header_candidates = []
        for i in range(chem_idx, min(len(lines), chem_idx + 50)):
            found = {}
            # Aggregate over a short vertical window because scanned tables can
            # split a multi-line header such as "Molyb- / denum, %" across OCR lines.
            for j in range(i, min(len(lines), i + 4)):
                for w in lines[j]:
                    e = header_element(w["text"])
                    if e and e not in found:
                        found[e] = w["xc"]
            if len(found) >= 3:
                header_candidates.append((len(found), i, found))
        if not header_candidates:
            continue
        _, header_idx, anchors = max(header_candidates, key=lambda x: x[0])
        if len(anchors) < 3:
            continue

        target_compact = compact(target_grade)
        grade_line = None
        grade_word = None
        for i in range(header_idx + 1, min(len(lines), header_idx + 55)):
            for w in lines[i]:
                token = compact(w["text"])
                # Handle OCR punctuation and combined cells such as "8M, 8MA".
                if (token == target_compact or token.startswith(target_compact + ",")
                        or token.startswith(target_compact + "/") or token.startswith(target_compact + "8ma")):
                    grade_line = i
                    grade_word = w
                    break
            if grade_line is not None:
                break
        if grade_line is None:
            continue

        # Use the detected grade line plus immediate neighboring lines. ASTM rows
        # sometimes wrap the Material cell, while the chemistry numbers stay on
        # the grade line.
        yc = grade_word["yc"]
        row_words = []
        for line in lines[max(0, grade_line - 1): min(len(lines), grade_line + 2)]:
            for w in line:
                if abs(w["yc"] - yc) <= 60:
                    row_words.append(w)

        ordered_anchors = sorted(anchors.items(), key=lambda kv: kv[1])
        x_centers = [x for _, x in ordered_anchors]
        requirements: dict[str, dict[str, Any]] = {}
        for pos, (element, x) in enumerate(ordered_anchors):
            left = (x_centers[pos - 1] + x) / 2.0 if pos > 0 else x - 60.0
            right = (x + x_centers[pos + 1]) / 2.0 if pos + 1 < len(x_centers) else x + 60.0
            cell_words = [w for w in row_words if left <= w["xc"] < right]
            cell_text = " ".join(w["text"] for w in sorted(cell_words, key=lambda w: w["xc"]))
            parsed = parse_requirement(cell_text)
            if parsed:
                requirements[element] = parsed

        if len(requirements) >= 3:
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

    try:
        requirements = extract_reference_requirements(reference_tables, test_grade)
    except ValueError:
        requirements = _reference_requirements_from_ocr(reference_ocr or {}, test_grade)
        if not requirements:
            raise

    observed = extract_observed_composition(test_tables)
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

      validation = compare(requirments, observed)
      return {
        refernce_document: {"standard": ref_standard, "source_text": ref_standard_text},
        "test document":{
            "stnadard": test_standard,"grade": test_grade,
            standard_text": test_standard_text, "grade_text": test_grade_text, 
        
        }

        standard:test_standard, "grade": test_grade,
        "reference_requirments:" requirments,
        "obsetved_composition": observed,
        'validation_result": validation,'
        '"error':None,
    }

    def validate_two_documents(
            reference_tables: Dict[str, Any],
            test_tables: Dict[str, Any],
            reference_text: str = "",
            test_text: str = "",
            reference_ocr: Optional[Dict[str, Any]] = None,
            test_ocr: Optional[Dict[str, Any]] = None,

            
    )
        

    def compare(reference_requirments: dict[str, dict[str, Any]], observed: dict[str, float]) -> dict[str, Any]:
        elements = []
        
    }