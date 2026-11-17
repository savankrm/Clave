import pytest

from clave import InvalidIdentifier
from clave.identifiers import identifier, secret_identifier


@pytest.mark.parametrize(
    "value",
    [
        "",
        "a",
        ".a",
        "a.",
        "a.b.c",
        "a b.c",
        " a.b",
        "a.b ",
        "a\\b.c",
        "a" * 65 + ".b",
        "é.a",
        "a/b.c",
        "a.1b",
        "a." + "x" * 65,
        "a.b\n",
    ],
)
def test_identifiers(value):
    with pytest.raises(InvalidIdentifier):
        identifier(value)


def test_identifier_boundaries():
    assert identifier("A_9.x-y") == ("A_9", "x-y")
    assert identifier("a" * 64 + "." + "b" * 64) == ("a" * 64, "b" * 64)
    assert secret_identifier("api_token") == ("api_token", "")
    assert secret_identifier("api_token.qa") == ("api_token", "qa")


@pytest.mark.parametrize("value", ["", "api.token.extra", "api token", "1token", "é"])
def test_secret_identifiers(value):
    with pytest.raises(InvalidIdentifier):
        secret_identifier(value)


def test_identifiers_preserve_case():
    assert identifier("My_Topic.Dev-1") == ("My_Topic", "Dev-1")
    assert secret_identifier("API_Key") == ("API_Key", "")
