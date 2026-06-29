from unittest.mock import patch, MagicMock
import pytest


def make_mock_sb(rows):
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = rows
    mock.table.return_value.insert.return_value.execute.return_value.data = []
    mock.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    return mock


@patch("pantry.get_supabase_client")
def test_get_pantry_returns_names(mock_sb):
    mock_sb.return_value = make_mock_sb([
        {"ingredient_name": "chicken breast"},
        {"ingredient_name": "eggs"},
    ])
    from pantry import get_pantry
    result = get_pantry("mvp-user")
    assert result == ["chicken breast", "eggs"]


@patch("pantry.get_supabase_client")
def test_get_pantry_empty(mock_sb):
    mock_sb.return_value = make_mock_sb([])
    from pantry import get_pantry
    result = get_pantry("mvp-user")
    assert result == []


@patch("pantry.get_supabase_client")
def test_add_to_pantry_normalizes_name(mock_sb):
    sb = make_mock_sb([{"ingredient_name": "chicken breast"}])
    mock_sb.return_value = sb
    from pantry import add_to_pantry
    result = add_to_pantry("mvp-user", "  Chicken Breast  ")
    insert_call = sb.table.return_value.insert
    insert_call.assert_called_once()
    inserted_row = insert_call.call_args[0][0]
    assert inserted_row["ingredient_name"] == "chicken breast"
    assert inserted_row["user_id"] == "mvp-user"
    assert result == ["chicken breast"]


@patch("pantry.get_supabase_client")
def test_add_to_pantry_returns_updated_list(mock_sb):
    sb = make_mock_sb([
        {"ingredient_name": "chicken breast"},
        {"ingredient_name": "eggs"},
    ])
    mock_sb.return_value = sb
    from pantry import add_to_pantry
    result = add_to_pantry("mvp-user", "eggs")
    assert result == ["chicken breast", "eggs"]


@patch("pantry.get_supabase_client")
def test_remove_from_pantry(mock_sb):
    sb = make_mock_sb([{"ingredient_name": "eggs"}])
    mock_sb.return_value = sb
    from pantry import remove_from_pantry
    result = remove_from_pantry("mvp-user", "  Chicken Breast  ")
    delete_chain = sb.table.return_value.delete.return_value.eq.return_value.eq
    delete_chain.assert_called()
    assert result == ["eggs"]


@patch("pantry.get_supabase_client")
def test_remove_from_pantry_returns_remaining(mock_sb):
    sb = make_mock_sb([])
    mock_sb.return_value = sb
    from pantry import remove_from_pantry
    result = remove_from_pantry("mvp-user", "chicken")
    assert result == []
