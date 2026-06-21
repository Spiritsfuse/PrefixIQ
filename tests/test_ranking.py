import pytest
from unittest.mock import MagicMock
from backend.app.ranking import get_suggestions_basic, get_suggestions_enhanced

def test_get_suggestions_basic_queries_correctly():
    mock_db = MagicMock()
    mock_result = [
        MagicMock(query="iphone", search_count=1000, score=1000.0),
        MagicMock(query="iphone 15", search_count=800, score=800.0)
    ]
    mock_db.execute.return_value.fetchall.return_value = mock_result
    
    res = get_suggestions_basic(mock_db, "iph", limit=5)
    
    # Check that database query was executed with correct parameters
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args[0][1]
    assert call_args["pattern"] == "iph%"
    assert call_args["limit"] == 5
    
    assert len(res) == 2
    assert res[0][0] == "iphone"
    assert res[0][1] == 1000
    assert res[0][2] == 1000.0

def test_get_suggestions_enhanced_queries_correctly():
    mock_db = MagicMock()
    mock_result = [
        MagicMock(query="chatgpt 5 release date", search_count=500, score=8.5),
        MagicMock(query="apple watch review", search_count=2000, score=7.2)
    ]
    mock_db.execute.return_value.fetchall.return_value = mock_result
    
    res = get_suggestions_enhanced(mock_db, "chat", limit=10)
    
    # Check that database query was executed with decay parameters
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args[0][1]
    assert call_args["pattern"] == "chat%"
    assert "decay_rate" in call_args
    assert call_args["limit"] == 10
    
    assert len(res) == 2
    assert res[0][0] == "chatgpt 5 release date"
    assert res[0][1] == 500
    assert res[0][2] == 8.5
