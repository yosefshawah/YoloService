import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from unittest.mock import patch, MagicMock
from dependencies import auth
from fastapi import Request


def make_credentials(username=None, password=None):
    # password must be a string, empty string if None
    return HTTPBasicCredentials(username=username, password=password or "")

def make_request():
    return MagicMock(spec=Request)


@patch("dependencies.auth.sqlite3.connect")
def test_get_current_user_id_anonymous(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchone.return_value = (999,)

    creds = None
    request = make_request()

    user_id = auth.get_current_user_id(request, creds)

    # Check the insert query was called ignoring whitespace issues:
    calls = [call.args[0].strip() for call in mock_cursor.execute.call_args_list]
    assert any("INSERT OR IGNORE INTO users (username, password)" in c for c in calls)

    assert user_id == 999


@patch("dependencies.auth.sqlite3.connect")
def test_get_current_user_id_username_no_password(mock_connect):
    creds = make_credentials(username="user", password=None)
    request = make_request()

    with pytest.raises(HTTPException) as e:
        auth.get_current_user_id(request, creds)

    assert e.value.status_code == 401
    assert "Password is required" in e.value.detail


@patch("dependencies.auth.sqlite3.connect")
def test_get_current_user_id_user_not_exists_auto_create_fail(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    creds = make_credentials(username="newuser", password="newpass")
    request = make_request()

    mock_cursor.fetchone.side_effect = [None]  # user not found on SELECT

    def execute_side_effect(query, params=None):
        if query.strip().startswith("INSERT INTO users"):
            raise auth.sqlite3.IntegrityError()
        else:
            return None

    mock_cursor.execute.side_effect = execute_side_effect

    with pytest.raises(HTTPException) as e:
        auth.get_current_user_id(request, creds)

    assert e.value.status_code == 500
    assert "User creation failed" in e.value.detail
    
    
@patch("dependencies.auth.sqlite3.connect")
def test_get_current_user_id_wrong_password(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Credentials with existing username but wrong password
    creds = make_credentials(username="existinguser", password="wrongpass")
    request = make_request()

    # Mock user found in DB with password "correctpass"
    mock_cursor.fetchone.side_effect = [(1, "correctpass")]

    # Mock execute just returns None (normal)
    mock_cursor.execute.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user_id(request, creds)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Incorrect password."

