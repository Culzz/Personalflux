from app.services.catalog_import import build_product_row, read_export


def test_row_uses_placeholder_title_and_marks_source():
    row = build_product_row(12, "1532")
    assert row["source_item_id"] == 12
    assert row["catalog_source"] == "retailrocket"
    assert "12" in row["title"]
    assert row["category"] == "Category 1532"
    assert row["is_active"] is True


def test_missing_category_stays_missing():
    assert build_product_row(1, "")["category"] is None
    assert build_product_row(1, "  ")["category"] is None
    assert build_product_row(1, None)["category"] is None


def test_read_export_parses_csv(tmp_path):
    path = tmp_path / "catalog.csv"
    path.write_text("source_item_id,category_id\n10,5\n11,\n", encoding="utf-8")
    rows = list(read_export(path))
    assert [row["source_item_id"] for row in rows] == [10, 11]
    assert rows[1]["category"] is None
