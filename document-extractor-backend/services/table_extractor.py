import re

import pandas as pd

from config import (
    COL_COUNT_TOLERANCE,
    COLUMN_TOLERANCE_MULTIPLIER,
    GAP_FACTOR,
    HEADER_NUMERIC_RATIO_THRESHOLD,
    MIN_COLS_FOR_TABLE,
    MIN_ROWS_PER_BLOCK,
)
from utils import get_box_metrics, is_numeric


def group_rows(detections: list, y_tolerance_ratio: float = 0.6) -> list:
    """Cell 12: Group OCR detections into rows using bounding box y-position. Unchanged."""
    items = []
    for d in detections:
        m = get_box_metrics(d["bbox"])
        items.append({**d, **m})
    items.sort(key=lambda d: d["y_center"])

    rows = []
    for item in items:
        placed = False
        for row in rows:
            avg_h = sum(x["height"] for x in row) / len(row)
            tol = avg_h * y_tolerance_ratio
            row_y = sum(x["y_center"] for x in row) / len(row)
            if abs(item["y_center"] - row_y) <= tol:
                row.append(item)
                placed = True
                break
        if not placed:
            rows.append([item])

    for row in rows:
        row.sort(key=lambda x: x["x_min"])

    rows.sort(key=lambda row: sum(x["y_center"] for x in row) / len(row))
    return rows


def detect_table_blocks(
    rows: list,
    min_cols: int = MIN_COLS_FOR_TABLE,
    gap_factor: float = GAP_FACTOR,
    min_rows: int = MIN_ROWS_PER_BLOCK,
    col_tol: int = COL_COUNT_TOLERANCE,
) -> list:
    """
    Cell 13 (updated): Detect contiguous table blocks — splits 
    
    """
    blocks = []
    current_block = []
    prev_row_y = None
    prev_avg_height = None
    prev_col_count = None

    for row in rows:
        avg_height = sum(r["height"] for r in row) / len(row)
        row_y = sum(r["y_center"] for r in row) / len(row)
        col_count = len(row)
        is_table_row = col_count >= min_cols

        gap_too_large = False
        if prev_row_y is not None and prev_avg_height is not None:
            gap = row_y - prev_row_y
            if gap > prev_avg_height * gap_factor:
                gap_too_large = True

        structure_changed = False
        if prev_col_count is not None:
            if abs(col_count - prev_col_count) > col_tol:
                structure_changed = True

        if is_table_row and not gap_too_large and not structure_changed:
            current_block.append(row)
        elif is_table_row:
            if len(current_block) >= min_rows:
                blocks.append(current_block)
            current_block = [row]
        else:
            if len(current_block) >= min_rows:
                blocks.append(current_block)
            current_block = []
            prev_col_count = None

        prev_row_y = row_y
        prev_avg_height = avg_height
        if is_table_row:
            prev_col_count = col_count

    if len(current_block) >= min_rows:
        blocks.append(current_block)

    return blocks


def detect_columns(block: list, tol_multiplier: float = COLUMN_TOLERANCE_MULTIPLIER) -> list:
    """Cell 14: Detect column boundaries inside a table block via x-position clustering. Unchanged."""
    all_items = [item for row in block for item in row]
    avg_height = sum(item["height"] for item in all_items) / len(all_items)
    x_tol = avg_height * tol_multiplier

    x_starts = sorted(item["x_min"] for item in all_items)

    clusters = []
    for x in x_starts:
        placed = False
        for cluster in clusters:
            if abs(x - cluster[-1]) <= x_tol:
                cluster.append(x)
                placed = True
                break
        if not placed:
            clusters.append([x])

    column_boundaries = sorted(sum(c) / len(c) for c in clusters)
    return column_boundaries


def assign_to_column(item: dict, column_boundaries: list) -> int:
    """Cell 14: assign a detection to its nearest column boundary. Unchanged."""
    x = item["x_min"]
    distances = [abs(x - b) for b in column_boundaries]
    return distances.index(min(distances))


def row_looks_like_header(row_cells: list) -> bool:
    """
    Cell 15: a row is treated as a header if fewer than
    HEADER_NUMERIC_RATIO_THRESHOLD of its non-empty cells are numeric.
    Unchanged.
    """
    non_empty = [c for c in row_cells if c.strip()]
    if not non_empty:
        return False
    numeric_count = sum(
        1 for c in non_empty
        if is_numeric(re.sub(r"[^0-9.\-]", "", c)) and c.strip() != ""
    )
    return (numeric_count / len(non_empty)) < HEADER_NUMERIC_RATIO_THRESHOLD


def build_dataframe(block: list) -> pd.DataFrame:
    """Cell 15: Convert a table block into a pandas DataFrame. Unchanged."""
    column_boundaries = detect_columns(block)
    num_cols = len(column_boundaries)

    table_data = []
    for row in block:
        row_cells = [""] * num_cols
        for item in row:
            col_idx = assign_to_column(item, column_boundaries)
            if row_cells[col_idx]:
                row_cells[col_idx] = (row_cells[col_idx] + " " + item["text"]).strip()
            else:
                row_cells[col_idx] = item["text"]
        table_data.append(row_cells)

    if len(table_data) > 1 and row_looks_like_header(table_data[0]):
        header_row = table_data[0]
        columns = [h.strip() if h.strip() else f"col_{i}" for i, h in enumerate(header_row)]
        df = pd.DataFrame(table_data[1:], columns=columns)
    else:
        columns = [f"col_{i}" for i in range(num_cols)]
        df = pd.DataFrame(table_data, columns=columns)

    return df


def extract_tables_from_page(detections: list) -> list:
    """Cell 16: Extract all tables from a single page's detections. Unchanged."""
    rows = group_rows(detections)
    blocks = detect_table_blocks(rows)
    tables = [build_dataframe(block) for block in blocks]
    return tables


def extract_all_tables(raw_output: dict) -> dict:
    """
    Cell 17: Run table reconstruction across every page.

    
    """
    all_pages_tables = {}

    for page_key, detections in raw_output.items():
        tables = extract_tables_from_page(detections)

        page_tables = []
        for df in tables:
            page_tables.append({
                "rows": df.shape[0],
                "cols": df.shape[1],
                "columns": list(df.columns),
                "data": df.to_dict(orient="records"),
            })

        all_pages_tables[page_key] = page_tables

    return all_pages_tables
