import re

from .exceptions import InvalidIdentifier, InvalidValue

COMPONENT = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}", re.ASCII)


def component(value: str, label: str) -> str:
    if not isinstance(value, str) or COMPONENT.fullmatch(value) is None:
        raise InvalidIdentifier(
            f"Invalid {label}: use 1–64 ASCII letters, digits, _ or -, "
            "starting with a letter."
        )
    return value


def environment(value: str) -> str:
    return component(value, "environment")


def identifier(value: str) -> tuple[str, str]:
    if not isinstance(value, str) or value.count(".") != 1:
        raise InvalidIdentifier(
            "Identifier must be topic.environment with exactly one dot."
        )
    topic, env = value.split(".")
    component(topic, "topic")
    environment(env)
    return topic, env


def secret_identifier(value: str) -> tuple[str, str]:
    if not isinstance(value, str) or value.count(".") > 1:
        raise InvalidIdentifier("Secret identifier must be topic or topic.environment.")
    if "." in value:
        return identifier(value)
    return component(value, "secret identifier"), ""


def nonblank(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidValue("Values must be nonblank strings.")
