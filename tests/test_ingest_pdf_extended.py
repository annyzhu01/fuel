import json
import pytest
from unittest.mock import patch, MagicMock
from ingest_pdf import _parse_json_response, map_recipe_pdf, insert_recipe_pdf, insert_pdf_recipes


# --- _parse_json_response ---

class TestParseJsonResponse:
    def test_plain_json_array(self):
        result = _parse_json_response('[{"title": "Soup"}]')
        assert result == [{"title": "Soup"}]

    def test_json_with_whitespace(self):
        result = _parse_json_response('  [{"title": "Soup"}]  ')
        assert result == [{"title": "Soup"}]

    def test_json_in_markdown_fences(self):
        text = '```json\n[{"title": "Soup"}]\n```'
        result = _parse_json_response(text)
        assert result == [{"title": "Soup"}]

    def test_json_in_plain_fences(self):
        text = '```\n[{"title": "Soup"}]\n```'
        result = _parse_json_response(text)
        assert result == [{"title": "Soup"}]

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response("not json at all")

    def test_empty_array(self):
        result = _parse_json_response("[]")
        assert result == []


# --- map_recipe_pdf ---

class TestMapRecipePdf:
    def test_full_mapping(self):
        raw = {
            "title": "Chocolate Cake",
            "description": "Rich and moist.",
            "steps": ["Mix", "Bake"],
            "category": "dessert",
            "keywords": ["chocolate", "cake"],
            "servings": 8,
            "calories": 350,
            "fat_g": 18,
            "carbohydrate_g": 40,
            "protein_g": 5,
        }
        result = map_recipe_pdf(raw, "cookbook.pdf")
        assert result["title"] == "Chocolate Cake"
        assert result["description"] == "Rich and moist."
        assert result["steps"] == ["Mix", "Bake"]
        assert result["source_url"] == "pdf:cookbook.pdf"
        assert result["calories"] == 350.0
        assert result["protein_g"] == 5.0

    def test_missing_fields_default(self):
        raw = {"title": "Plain"}
        result = map_recipe_pdf(raw, "test.pdf")
        assert result["title"] == "Plain"
        assert result["steps"] == []
        assert result["keywords"] == []
        assert result["calories"] is None
        assert result["source_url"] == "pdf:test.pdf"

    def test_string_servings_parsed(self):
        raw = {"title": "Dish", "servings": "4"}
        result = map_recipe_pdf(raw, "x.pdf")
        assert result["servings"] == 4.0


# --- insert_recipe_pdf ---

class TestInsertRecipePdf:
    def test_returns_id_on_success(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "r-123"}]
        result = insert_recipe_pdf(mock_sb, {"title": "Test"})
        assert result == "r-123"

    def test_duplicate_returns_none(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.side_effect = Exception("23505 duplicate key")
        result = insert_recipe_pdf(mock_sb, {"title": "Dup"})
        assert result is None

    def test_other_exception_raised(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.side_effect = Exception("connection timeout")
        with pytest.raises(Exception, match="connection timeout"):
            insert_recipe_pdf(mock_sb, {"title": "Fail"})


# --- insert_pdf_recipes ---

class TestInsertPdfRecipes:
    def test_inserts_and_counts(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "r-1"}]
        mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "i-1"}]
        recipes = [
            {"title": "Soup", "ingredients": [{"name": "salt", "quantity": "1 tsp"}]},
        ]
        inserted, skipped = insert_pdf_recipes(mock_sb, recipes, "cook.pdf")
        assert inserted == 1
        assert skipped == 0

    def test_skips_no_title(self, capsys):
        mock_sb = MagicMock()
        recipes = [{"ingredients": []}]
        inserted, skipped = insert_pdf_recipes(mock_sb, recipes, "cook.pdf")
        assert inserted == 0
        captured = capsys.readouterr()
        assert "no title" in captured.out.lower()

    def test_skips_duplicates(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.side_effect = Exception("23505 duplicate")
        recipes = [{"title": "Dup Recipe", "ingredients": []}]
        inserted, skipped = insert_pdf_recipes(mock_sb, recipes, "cook.pdf")
        assert inserted == 0
        assert skipped == 1

    def test_handles_insert_error(self, capsys):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.side_effect = Exception("connection error")
        recipes = [{"title": "Error Recipe", "ingredients": []}]
        inserted, skipped = insert_pdf_recipes(mock_sb, recipes, "cook.pdf")
        assert inserted == 0
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
