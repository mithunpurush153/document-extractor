"""
Chemical Composition Validator Service

Validates supplier material certificates against ASTM standards.
Currently supports ASTM A194/A194M Grade 8M.

The validator is deterministic: no ML/AI is used for PASS/FAIL.
It consumes the existing tables_by_page structure without modifying
the existing table extractor.
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple


class ChemicalValidator:
    """Validate chemical composition against reference standards."""

    def __init__(self):
        self.reference_data = self._load_reference_data()

    def _load_reference_data(self) -> Dict[str, Any]:
        ref_dir = Path(__file__).parent / "reference_data"
        ref_data: Dict[str, Any] = {}
        a194_path = ref_dir / "a194.json"
        if a194_path.exists():
            with open(a194_path, "r", encoding="utf-8") as f:
                ref_data["a194"] = json.load(f)
        return ref_data 

    def identify_standard_and_grade(
        self, tables_data: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[str]]:
        standard = None
        grade = None

        for tables_list in tables_data.values():
            if not isinstance(tables_list, list):
                continue
            for table in tables_list:
                if not isinstance(table, dict):
                    continue
                table_text = self._table_to_text(table).upper()

                if "A194" in table_text:
                    standard = "ASTM A194/A194M"

                    # OCR may produce "GRADES 8M", "GRADE 8M", etc.
                    if re.search(r"\b8M\b", table_text) or "GRADE 8M" in table_text:
                        grade = "8M"

        return standard, grade

    def extract_chemical_composition(
        self,
        tables_data: Dict[str, Any],
        standard: str,
        grade: str,
    ) -> Dict[str, Optional[float]]:
        composition = {
            "carbon": None,
            "manganese": None,
            "phosphorus": None,
            "sulfur": None,
            "silicon": None,
            "chromium": None,
            "nickel": None,
            "molybdenum": None,
            "nitrogen": None,
        }

        for tables_list in tables_data.values():
            if not isinstance(tables_list, list):
                continue

            for table in tables_list:
                if not isinstance(table, dict):
                    continue

                extracted = self._extract_chemical_table(table)
                for element, value in extracted.items():
                    if value is not None and composition[element] is None:
                        composition[element] = value

        return composition

    @staticmethod
    def _normalise_ocr_header(value: Any) -> str:
        """
        Normalize OCR/table-header variants.

        Examples seen in the real M16 extraction:
        %C -> %C
        96C -> %C
        %6Mn -> %MN
        96S -> %S
        96Si -> %SI
        $6Cr -> %CR
        Ni -> NI
        Mo -> MO
        """
        s = str(value or "").strip().upper()
        if not s:
            return ""

        # Common OCR corruption of the percent sign.
        s = s.replace("96", "%")
        s = s.replace("$6", "%")
        s = s.replace("%6", "%")

        # Remove spaces and punctuation that OCR can introduce.
        s = re.sub(r"[\s_\-]", "", s)

        aliases = {
            "%C": "carbon",
            "C": "carbon",
            "%CARBON": "carbon",
            "CARBON": "carbon",

            "%MN": "manganese",
            "MN": "manganese",
            "MANGANESE": "manganese",

            "%P": "phosphorus",
            "P": "phosphorus",
            "PHOSPHORUS": "phosphorus",

            "%S": "sulfur",
            "S": "sulfur",
            "SULFUR": "sulfur",
            "SULPHUR": "sulfur",

            "%SI": "silicon",
            "SI": "silicon",
            "SILICON": "silicon",

            "%CR": "chromium",
            "CR": "chromium",
            "CHROMIUM": "chromium",

            "NI%": "nickel",
            "NI": "nickel",
            "NICKEL": "nickel",

            "MO": "molybdenum",
            "MOLYBDENUM": "molybdenum",

            "N": "nitrogen",
            "N%": "nitrogen",
            "NITROGEN": "nitrogen",
        }
        return aliases.get(s, "")

    def _extract_chemical_table(
        self, table: Dict[str, Any]
    ) -> Dict[str, Optional[float]]:
        """
        Extract a chemistry table from the existing tables_by_page shape.

        Supports both:
        1. normal tables whose column names are chemical symbols, and
        2. the real certificate layout where chemical symbols are in a
           PARTICULARS row and observed values are in an OBSERVED row.
        """
        extracted = {
            "carbon": None,
            "manganese": None,
            "phosphorus": None,
            "sulfur": None,
            "silicon": None,
            "chromium": None,
            "nickel": None,
            "molybdenum": None,
            "nitrogen": None,
        }

        columns = table.get("columns") or []
        rows = table.get("data") or []
        if not rows:
            return extracted

        # Build a stable ordered list of (column key, value) pairs.
        ordered_rows: List[Dict[str, Any]] = [
            r for r in rows if isinstance(r, dict)
        ]

        # First try the certificate's actual structure:
        # row 1: PARTICULARS + chemical symbols
        # row 2: SPECIFIED ... MIN
        # row 3: SPECIFIED ... MAX
        # row 4: OBSERVED COMPOSITIONS + observed values
        header_row = None
        observed_row = None

        for row in ordered_rows:
            text = " ".join(str(v).upper() for v in row.values() if v)
            if "PARTICULAR" in text and any(
                self._normalise_ocr_header(v) in {
                    "carbon", "manganese", "phosphorus", "sulfur",
                    "silicon", "chromium", "nickel", "molybdenum"
                }
                for v in row.values()
            ):
                header_row = row

            if "OBSERVED" in text and (
                "COMPOSITION" in text or "COMPOSITIONS" in text
            ):
                observed_row = row

        if header_row is not None and observed_row is not None:
            for key, header_value in header_row.items():
                element = self._normalise_ocr_header(header_value)
                if element in extracted:
                    value = self._to_float(observed_row.get(key))
                    if value is not None:
                        extracted[element] = value

            if any(v is not None for v in extracted.values()):
                return extracted

        # Fallback: column headers themselves contain the chemical symbols.
        col_to_element: Dict[str, str] = {}
        for col in columns:
            element = self._normalise_ocr_header(col)
            if element in extracted:
                col_to_element[col] = element

        for row in ordered_rows:
            text = " ".join(str(v).upper() for v in row.values() if v)
            if not any(marker in text for marker in ("OBSERVED", "RESULT", "ANALYSE")):
                continue

            for col, element in col_to_element.items():
                value = self._to_float(row.get(col))
                if value is not None:
                    extracted[element] = value

        return extracted

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip().replace(",", "")
        if not text:
            return None

        # Accept strings containing a numeric value, while avoiding
        # accidentally interpreting ordinary text as a number.
        match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", text)
        if not match:
            return None

        try:
            return float(match.group(0))
        except ValueError:
            return None

    def validate_composition(
        self,
        observed: Dict[str, Optional[float]],
        standard: str,
        grade: str,
    ) -> Dict[str, Any]:
        std_key = "a194" if "A194" in standard.upper() else None

        if not std_key or std_key not in self.reference_data:
            return {"error": f"Standard {standard} not found in reference data"}

        std_data = self.reference_data[std_key]
        grades = std_data.get("grades", {})
        if grade not in grades:
            return {"error": f"Grade {grade} not found for standard {standard}"}

        spec = grades[grade].get("chemical_composition", {})
        results: List[Dict[str, Any]] = []

        for element_key, element_spec in spec.items():
            element_name = element_spec.get("element_name", element_key)
            observed_value = observed.get(element_key)

            result = {
                "element": element_name,
                "symbol": element_spec.get("symbol", ""),
                "requirement": element_spec.get("type"),
                "observed": observed_value,
                "status": "NOT_REPORTED",
                "note": "",
            }

            spec_type = element_spec.get("type")

            if spec_type == "NOT_REPORTED":
                result["status"] = "NOT_REPORTED"
                result["note"] = element_spec.get("note", "")
                result["requirement_text"] = "Not reported by supplier"
                results.append(result)
                continue

            if observed_value is None:
                result["status"] = "NOT_REPORTED"
                result["note"] = "Value not found in supplier document"
                result["requirement_text"] = "Value not reported"
                results.append(result)
                continue

            if spec_type == "MAX":
                max_val = element_spec.get("max_value")
                result["requirement_text"] = f"≤ {max_val}"
                result["status"] = (
                    "PASS" if observed_value <= max_val else "FAIL"
                )

            elif spec_type == "MIN":
                min_val = element_spec.get("min_value")
                result["requirement_text"] = f"≥ {min_val}"
                result["status"] = (
                    "PASS" if observed_value >= min_val else "FAIL"
                )

            elif spec_type == "RANGE":
                min_val = element_spec.get("min_value")
                max_val = element_spec.get("max_value")
                result["requirement_text"] = f"{min_val} – {max_val}"
                result["status"] = (
                    "PASS"
                    if min_val <= observed_value <= max_val
                    else "FAIL"
                )

            results.append(result)

        return {
            "elements": results,
            "summary": self._get_summary(results),
        }

    @staticmethod
    def _get_summary(results: List[Dict[str, Any]]) -> Dict[str, int]:
        summary = {"total": len(results), "pass": 0, "fail": 0, "not_reported": 0}
        for result in results:
            status = result.get("status", "NOT_REPORTED")
            if status == "PASS":
                summary["pass"] += 1
            elif status == "FAIL":
                summary["fail"] += 1
            else:
                summary["not_reported"] += 1
        return summary

    @staticmethod
    def _table_to_text(table: Dict[str, Any]) -> str:
        text_parts: List[str] = []

        if "columns" in table:
            text_parts.extend(str(c) for c in table["columns"])

        if "data" in table:
            for row in table["data"]:
                if isinstance(row, dict):
                    text_parts.extend(str(v) for v in row.values() if v)

        return " ".join(text_parts)

    def validate_supplier_document(
        self, extraction_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        tables_data = extraction_result.get("tables_by_page", {})

        standard, grade = self.identify_standard_and_grade(tables_data)

        if not standard or not grade:
            return {
                "identified_standard": None,
                "identified_grade": None,
                "validation_result": None,
                "error": "Could not identify ASTM standard or material grade from supplier document",
            }

        observed_composition = self.extract_chemical_composition(
            tables_data, standard, grade
        )

        validation_result = self.validate_composition(
            observed_composition, standard, grade
        )

        return {
            "identified_standard": standard,
            "identified_grade": grade,
            "reference": "A194",
            "observed_composition": observed_composition,
            "validation_result": validation_result,
            "error": None,
        }