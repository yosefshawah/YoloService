import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from unittest.mock import patch, MagicMock
from dependencies import auth
from fastapi import Request
from sqlalchemy.exc import IntegrityError
from models.models import User


def make_credentials(username=None, password=None):
    return HTTPBasicCredentials(username=username, password=password or "")

def make_request():
    return MagicMock(spec=Request)


@patch("dependencies.auth.get_db")
def test_get_current_user_id_anonymous(mock_get_db):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db

    # Simulate anonymous user does not exist first, then gets created
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    created_user = User(id=999, username="__anonymous__", password="__none__")
    mock_db.add.side_effect = lambda user: setattr(user, 'id', 999)
    mock_db.commit.return_value = None
    mock_db.refresh.side_effect = lambda user: None

    creds = None
    request = make_request()
    user_id = auth.get_current_user_id(request, creds, db=mock_db)

    assert user_id == 999
    mock_db.add.assert_called()
    mock_db.commit.assert_called()


def test_get_current_user_id_username_no_password():
    creds = make_credentials(username="user", password=None)
    request = make_request()

    with pytest.raises(HTTPException) as e:
        auth.get_current_user_id(request, creds, db=MagicMock())

    assert e.value.status_code == 401
    assert "Password is required" in e.value.detail


@patch("dependencies.auth.get_db")
def test_get_current_user_id_user_not_exists_auto_create_fail(mock_get_db):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db

    creds = make_credentials(username="newuser", password="newpass")
    request = make_request()

    # User doesn't exist
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    # Raise IntegrityError on user creation
    mock_db.commit.side_effect = IntegrityError("fail", {}, None)

    with pytest.raises(HTTPException) as e:
        auth.get_current_user_id(request, creds, db=mock_db)

    assert e.value.status_code == 500
    assert "User creation failed" in e.value.detail
    mock_db.rollback.assert_called()


@patch("dependencies.auth.get_db")
def test_get_current_user_id_wrong_password(mock_get_db):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db

    creds = make_credentials(username="existinguser", password="wrongpass")
    request = make_request()

    existing_user = User(id=1, username="existinguser", password="correctpass")
    mock_db.query.return_value.filter_by.return_value.first.return_value = existing_user

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user_id(request, creds, db=mock_db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Incorrect password."
