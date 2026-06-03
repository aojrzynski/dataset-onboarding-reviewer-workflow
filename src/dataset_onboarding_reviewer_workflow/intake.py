"""Local-only dataset intake for CSV and Excel files.

Intake is the boundary where a user-provided file becomes internal workflow
state. It reads local files only, fails early for unsupported or unusable
inputs, and returns metadata that describes files, shape, sheets, and columns
without exposing raw rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

SUPPORTED_DATASET_EXTENSIONS = {".csv", ".xlsx", ".xlsm"}
EXCEL_DATASET_EXTENSIONS = {".xlsx", ".xlsm"}


class DatasetIntakeError(Exception):
    """Raised when a local dataset cannot be loaded safely."""


@dataclass(frozen=True)
class LoadedDataset:
    """A loaded dataframe plus safe metadata for orchestration.

    The dataframe is intentionally internal to the workflow state. Writers must
    use only the metadata/profile fields so raw rows stay out of JSON artifacts.
    """

    dataframe: pd.DataFrame
    metadata: dict[str, Any]


def _base_metadata(dataset_path: Path) -> dict[str, Any]:
    return {
        "source_path": str(dataset_path),
        "file_name": dataset_path.name,
        "file_extension": dataset_path.suffix.lower(),
        "file_size_bytes": dataset_path.stat().st_size,
    }


def _validate_loaded_dataframe(dataframe: pd.DataFrame, dataset_path: Path) -> None:
    """Fail early when there is no row-and-column structure to profile."""
    if dataframe.empty or len(dataframe.columns) == 0:
        raise DatasetIntakeError(
            f"Dataset '{dataset_path}' did not contain any rows and columns to profile."
        )


def _load_excel_dataset(dataset_path: Path, sheet: str | None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load one Excel sheet using deterministic selection.

    A named sheet must exist; otherwise the first workbook sheet is selected so
    repeated runs over the same file choose the same tab.
    """
    try:
        excel_file = pd.ExcelFile(dataset_path, engine="openpyxl")
    except ValueError as exc:
        raise DatasetIntakeError(f"Could not open Excel dataset '{dataset_path}': {exc}") from exc

    available_sheet_names = list(excel_file.sheet_names)
    if not available_sheet_names:
        raise DatasetIntakeError(f"Excel dataset '{dataset_path}' did not contain any sheets.")

    selected_sheet = sheet or available_sheet_names[0]
    if selected_sheet not in available_sheet_names:
        raise DatasetIntakeError(
            f"Sheet '{selected_sheet}' was not found in '{dataset_path}'. "
            f"Available sheets: {', '.join(available_sheet_names)}."
        )

    dataframe = pd.read_excel(excel_file, sheet_name=selected_sheet, engine="openpyxl")
    return dataframe, {
        "sheet_name": selected_sheet,
        "available_sheet_names": available_sheet_names,
    }


def load_dataset(dataset_path: Path | str, sheet: str | None = None) -> LoadedDataset:
    """Load a local CSV/XLSX/XLSM dataset and return safe load metadata.

    This function returns the dataframe for downstream aggregate profiling, but
    the metadata contains only file/load facts and column names, never row data.
    """

    path = Path(dataset_path)
    if not path.exists():
        raise DatasetIntakeError(f"Dataset file does not exist: {path}")
    if path.is_dir():
        raise DatasetIntakeError(f"Dataset path is a directory, not a file: {path}")

    extension = path.suffix.lower()
    if extension not in SUPPORTED_DATASET_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_DATASET_EXTENSIONS))
        raise DatasetIntakeError(
            f"Unsupported dataset extension '{extension or '<none>'}'. "
            f"Supported extensions: {supported}."
        )

    metadata = _base_metadata(path)
    try:
        if extension == ".csv":
            if sheet is not None:
                raise DatasetIntakeError("--sheet can only be used with .xlsx or .xlsm datasets.")
            dataframe = pd.read_csv(path)
        elif extension in EXCEL_DATASET_EXTENSIONS:
            dataframe, excel_metadata = _load_excel_dataset(path, sheet)
            metadata.update(excel_metadata)
        else:  # pragma: no cover - guarded by extension validation above.
            raise DatasetIntakeError(f"Unsupported dataset extension '{extension}'.")
    except pd.errors.EmptyDataError as exc:
        raise DatasetIntakeError(f"Dataset '{path}' is empty or has no columns.") from exc
    except DatasetIntakeError:
        raise
    except Exception as exc:
        raise DatasetIntakeError(f"Could not load dataset '{path}': {exc}") from exc

    _validate_loaded_dataframe(dataframe, path)
    # These metadata fields are safe artifact evidence: file/shape/column facts
    # without row samples, cell values, top values, or distinct value lists.
    metadata.update(
        {
            "row_count": int(len(dataframe)),
            "column_count": int(len(dataframe.columns)),
            "column_names": [str(column) for column in dataframe.columns],
        }
    )
    return LoadedDataset(dataframe=dataframe, metadata=metadata)
