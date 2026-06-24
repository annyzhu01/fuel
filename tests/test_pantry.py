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
