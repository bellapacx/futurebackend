from app.core.auth import CurrentUser


def test_current_user_model():
    u = CurrentUser(user_id="abc", email="x@example.com", role="authenticated")
    assert u.user_id == "abc"
    assert u.email == "x@example.com"