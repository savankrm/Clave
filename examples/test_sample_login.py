from clave import Credential


def demo_login(username: str, password: str) -> bool:
    """Stand in for the login call to an application under test."""
    return username == "demo-user" and password == "demo-only-password"


def test_sample_login(db_credentials: Credential) -> None:
    logged_in = demo_login(db_credentials.username, db_credentials.password)
    assert logged_in
