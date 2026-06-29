from embed_recipes import build_embedding_text


class TestBuildEmbeddingText:
    def test_title_only(self):
        recipe = {"title": "Chicken Soup"}
        result = build_embedding_text(recipe, [])
        assert "Chicken Soup" in result

    def test_title_duplicated(self):
        recipe = {"title": "Chicken Soup"}
        result = build_embedding_text(recipe, [])
        assert result.count("Chicken Soup") == 2

    def test_with_description(self):
        recipe = {"title": "Pasta", "description": "A hearty Italian dish."}
        result = build_embedding_text(recipe, [])
        assert "A hearty Italian dish." in result

    def test_boilerplate_description_excluded(self):
        recipe = {
            "title": "Pasta",
            "description": "Make and share this Pasta recipe from Food.com.",
        }
        result = build_embedding_text(recipe, [])
        assert "Make and share" not in result

    def test_with_ingredients(self):
        recipe = {"title": "Soup"}
        result = build_embedding_text(recipe, ["chicken", "salt", "water"])
        assert "Ingredients: chicken, salt, water" in result

    def test_with_category(self):
        recipe = {"title": "Soup", "category": "main-dish"}
        result = build_embedding_text(recipe, [])
        assert "Category: main-dish" in result

    def test_with_keywords(self):
        recipe = {"title": "Soup", "keywords": ["warm", "comfort"]}
        result = build_embedding_text(recipe, [])
        assert "Keywords: warm, comfort" in result

    def test_empty_recipe(self):
        recipe = {}
        result = build_embedding_text(recipe, [])
        assert result == ""

    def test_full_recipe(self):
        recipe = {
            "title": "Chicken Curry",
            "description": "A spicy Indian curry.",
            "category": "main-dish",
            "keywords": ["spicy", "indian"],
        }
        result = build_embedding_text(recipe, ["chicken", "curry paste"])
        assert "Chicken Curry" in result
        assert "A spicy Indian curry." in result
        assert "Ingredients: chicken, curry paste" in result
        assert "Category: main-dish" in result
        assert "Keywords: spicy, indian" in result

    def test_none_description_excluded(self):
        recipe = {"title": "Salad", "description": None}
        result = build_embedding_text(recipe, [])
        assert "None" not in result

    def test_empty_description_excluded(self):
        recipe = {"title": "Salad", "description": ""}
        result = build_embedding_text(recipe, [])
        parts = result.split(". ")
        assert all("" != p for p in parts)
