import pytest
from utils import parse_float, parse_list, clean_description, is_real_description


# --- parse_float ---

class TestParseFloat:
    def test_none_returns_none(self):
        assert parse_float(None) is None

    def test_int(self):
        assert parse_float(5) == 5.0

    def test_float(self):
        assert parse_float(3.14) == 3.14

    def test_string_int(self):
        assert parse_float("42") == 42.0

    def test_string_float(self):
        assert parse_float("3.14") == 3.14

    def test_invalid_string(self):
        assert parse_float("abc") is None

    def test_empty_string(self):
        assert parse_float("") is None

    def test_bool_true(self):
        assert parse_float(True) == 1.0

    def test_negative(self):
        assert parse_float("-7.5") == -7.5

    def test_zero(self):
        assert parse_float(0) == 0.0

    def test_non_convertible_type(self):
        assert parse_float([1, 2]) is None


# --- parse_list ---

class TestParseList:
    def test_already_a_list(self):
        assert parse_list(["a", "b"]) == ["a", "b"]

    def test_empty_list(self):
        assert parse_list([]) == []

    def test_none_returns_empty(self):
        assert parse_list(None) == []

    def test_empty_string(self):
        assert parse_list("") == []

    def test_na_string(self):
        assert parse_list("NA") == []

    def test_null_string(self):
        assert parse_list("NULL") == []

    def test_none_string(self):
        assert parse_list("None") == []

    def test_python_list_string(self):
        assert parse_list("['a', 'b', 'c']") == ["a", "b", "c"]

    def test_python_single_string_literal(self):
        assert parse_list("'hello'") == ["hello"]

    def test_python_list_of_numbers(self):
        assert parse_list("[1, 2, 3]") == [1, 2, 3]

    def test_r_style_c_notation(self):
        assert parse_list("c('x', 'y')") == ["x", "y"]

    def test_r_style_with_na(self):
        result = parse_list("c('a', NA, 'b')")
        assert result == ["a", "b"]

    def test_unparseable_returns_empty(self):
        assert parse_list("{not valid}") == []

    def test_single_element_eval(self):
        assert parse_list("42") == []

    def test_whitespace_only(self):
        assert parse_list("   ") == []


# --- clean_description ---

class TestCleanDescription:
    def test_none_returns_none(self):
        assert clean_description(None) is None

    def test_empty_string_returns_none(self):
        assert clean_description("") is None

    def test_real_description(self):
        assert clean_description("A tasty chicken dinner.") == "A tasty chicken dinner."

    def test_boilerplate_removed(self):
        assert clean_description("Make and share this Chicken Casserole recipe from Food.com.") is None

    def test_boilerplate_case_insensitive(self):
        assert clean_description("make and share this easy salad recipe from food.com.") is None

    def test_strips_whitespace(self):
        assert clean_description("  hello  ") == "hello"

    def test_boilerplate_without_trailing_period(self):
        assert clean_description("Make and share this Soup recipe from Food.com") is None


# --- is_real_description ---

class TestIsRealDescription:
    def test_none_returns_false(self):
        assert is_real_description(None) is False

    def test_empty_returns_false(self):
        assert is_real_description("") is False

    def test_whitespace_only_returns_false(self):
        assert is_real_description("   ") is False

    def test_real_desc_returns_true(self):
        assert is_real_description("A delicious pasta dish.") is True

    def test_boilerplate_returns_false(self):
        assert is_real_description("Make and share this Pasta recipe from Food.com.") is False

    def test_non_boilerplate_returns_true(self):
        assert is_real_description("Quick weeknight chicken stir fry") is True
