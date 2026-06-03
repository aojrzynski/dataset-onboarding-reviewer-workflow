from __future__ import annotations

import pandas as pd
import pytest
from openpyxl import Workbook

from dataset_onboarding_reviewer_workflow.intake import DatasetIntakeError, load_dataset


def write_csv(path):
    path.write_text("customer_id,signup_date,monthly_spend\nC001,2025-01-01,10.5\n", encoding="utf-8")


def test_load_dataset_loads_csv(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)

    loaded = load_dataset(csv_path)

    assert loaded.dataframe.shape == (1, 3)
    assert loaded.metadata["file_extension"] == ".csv"
    assert loaded.metadata["row_count"] == 1
    assert loaded.metadata["column_names"] == ["customer_id", "signup_date", "monthly_spend"]


def test_load_dataset_loads_xlsx_and_named_sheet(tmp_path) -> None:
    xlsx_path = tmp_path / "customers.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame({"ignored": [1]}).to_excel(writer, sheet_name="Ignore", index=False)
        pd.DataFrame({"customer_id": ["C001"], "region": ["North"]}).to_excel(
            writer, sheet_name="Customers", index=False
        )

    loaded = load_dataset(xlsx_path, sheet="Customers")

    assert loaded.dataframe.shape == (1, 2)
    assert loaded.metadata["sheet_name"] == "Customers"
    assert loaded.metadata["available_sheet_names"] == ["Ignore", "Customers"]


def test_load_dataset_loads_first_excel_sheet_deterministically(tmp_path) -> None:
    xlsx_path = tmp_path / "customers.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame({"first_sheet_column": [1]}).to_excel(writer, sheet_name="First", index=False)
        pd.DataFrame({"second_sheet_column": [2]}).to_excel(writer, sheet_name="Second", index=False)

    loaded = load_dataset(xlsx_path)

    assert loaded.metadata["sheet_name"] == "First"
    assert loaded.metadata["column_names"] == ["first_sheet_column"]


def test_load_dataset_loads_xlsm_when_practical(tmp_path) -> None:
    xlsm_path = tmp_path / "customers.xlsm"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Customers"
    worksheet.append(["customer_id", "region"])
    worksheet.append(["C001", "North"])
    workbook.save(xlsm_path)

    loaded = load_dataset(xlsm_path)

    assert loaded.metadata["file_extension"] == ".xlsm"
    assert loaded.metadata["sheet_name"] == "Customers"
    assert loaded.metadata["row_count"] == 1


def test_load_dataset_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(DatasetIntakeError, match="does not exist"):
        load_dataset(tmp_path / "missing.csv")


def test_load_dataset_rejects_directory(tmp_path) -> None:
    with pytest.raises(DatasetIntakeError, match="directory"):
        load_dataset(tmp_path)


def test_load_dataset_rejects_unsupported_extension(tmp_path) -> None:
    text_path = tmp_path / "customers.txt"
    text_path.write_text("not,a,supported,dataset\n", encoding="utf-8")

    with pytest.raises(DatasetIntakeError, match="Unsupported dataset extension"):
        load_dataset(text_path)


def test_load_dataset_rejects_empty_or_no_column_dataset(tmp_path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")

    with pytest.raises(DatasetIntakeError, match="empty|no columns"):
        load_dataset(csv_path)


def test_load_dataset_rejects_missing_sheet(tmp_path) -> None:
    xlsx_path = tmp_path / "customers.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame({"customer_id": ["C001"]}).to_excel(writer, sheet_name="Customers", index=False)

    with pytest.raises(DatasetIntakeError, match="was not found"):
        load_dataset(xlsx_path, sheet="Orders")
