from query_recipes import format_recipes_as_context, format_meal_as_context


class TestFormatRecipesAsContext:
    def test_empty_list(self):
        assert format_recipes_as_context([]) == "No recipes found."

    def test_single_recipe_title_only(self):
        recipes = [{"title": "Chicken Soup"}]
        result = format_recipes_as_context(recipes)
        assert "1. Chicken Soup" in result

    def test_recipe_with_category(self):
        recipes = [{"title": "Pasta", "category": "main-dish"}]
        result = format_recipes_as_context(recipes)
        assert "[main-dish]" in result

    def test_recipe_with_macros(self):
        recipes = [{
            "title": "Salad",
            "calories": 200.0,
            "protein_g": 15.0,
            "fat_g": 8.0,
            "carbohydrate_g": 20.0,
        }]
        result = format_recipes_as_context(recipes)
        assert "200 kcal" in result
        assert "15g protein" in result
        assert "8g fat" in result
        assert "20g carbs" in result

    def test_recipe_with_description(self):
        recipes = [{"title": "Soup", "description": "A warm hearty soup for cold days."}]
        result = format_recipes_as_context(recipes)
        assert "A warm hearty soup" in result

    def test_description_truncated_at_120_chars(self):
        long_desc = "A" * 200
        recipes = [{"title": "Dish", "description": long_desc}]
        result = format_recipes_as_context(recipes)
        assert "A" * 120 in result
        assert "A" * 121 not in result

    def test_multiple_recipes_numbered(self):
        recipes = [
            {"title": "Recipe A"},
            {"title": "Recipe B"},
            {"title": "Recipe C"},
        ]
        result = format_recipes_as_context(recipes)
        assert "1. Recipe A" in result
        assert "2. Recipe B" in result
        assert "3. Recipe C" in result

    def test_none_macros_excluded(self):
        recipes = [{"title": "Plain", "calories": None, "protein_g": None}]
        result = format_recipes_as_context(recipes)
        assert "kcal" not in result
        assert "protein" not in result


class TestFormatMealAsContext:
    def test_formats_mains_and_sides(self):
        meal = {
            "mains": [{"title": "Grilled Chicken"}],
            "sides": [{"title": "Steamed Broccoli"}],
        }
        result = format_meal_as_context(meal)
        assert "MAIN DISHES:" in result
        assert "SIDE DISHES:" in result
        assert "Grilled Chicken" in result
        assert "Steamed Broccoli" in result

    def test_empty_mains_and_sides(self):
        meal = {"mains": [], "sides": []}
        result = format_meal_as_context(meal)
        assert "No recipes found." in result

    def test_missing_keys_handled(self):
        result = format_meal_as_context({})
        assert "MAIN DISHES:" in result
        assert "SIDE DISHES:" in result
