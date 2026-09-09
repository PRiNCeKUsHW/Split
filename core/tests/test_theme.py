"""The palette and the theme toggle, asserted against the shipped CSS.

Colour regressions are silent: nothing crashes when text drops to 3:1. These
tests read app.css directly so the contract survives any future restyle.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

CSS = Path(settings.BASE_DIR) / "static" / "css" / "app.css"

# Entry points that do NOT extend base.html and so need their own head script.
STANDALONE_TEMPLATES = [
    "templates/accounts/login.html",
    "templates/accounts/set_password.html",
    "templates/core/offline.html",
]


# ----------------------------------------------------------------- helpers


def _css() -> str:
    return CSS.read_text(encoding="utf-8")


def _block(selector: str) -> str:
    """Return the body of the first rule whose selector matches exactly."""
    text = _css()
    index = text.index(selector)
    start = text.index("{", index) + 1
    depth, cursor = 1, start
    while depth:
        char = text[cursor]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        cursor += 1
    return text[start : cursor - 1]


def _tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"(--[a-z-]+):\s*([^;]+);", block))


def _relative_luminance(hex_colour: str) -> float:
    hex_colour = hex_colour.lstrip("#")
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    channels = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(foreground: str, background: str) -> float:
    a, b = _relative_luminance(foreground), _relative_luminance(background)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def _resolve(name: str, tokens: dict[str, str], fallback: dict[str, str]) -> str:
    key = f"--{name}"
    value = tokens.get(key, fallback.get(key, "")).strip()
    assert value.startswith("#"), f"{key} is {value!r}, expected a hex literal"
    return value


@pytest.fixture(scope="module")
def light() -> dict[str, str]:
    return _tokens(_block(":root {"))


@pytest.fixture(scope="module")
def dark(light) -> dict[str, str]:
    merged = dict(light)
    merged.update(_tokens(_block(':root[data-theme="dark"]')))
    return merged


# ------------------------------------------------------- the two dark blocks


def test_a_forced_dark_block_exists():
    """Without it the toggle cannot force dark on a light-mode phone."""
    assert ':root[data-theme="dark"]' in _css()


def test_the_system_dark_block_is_guarded_against_a_forced_light_choice():
    assert ':root:not([data-theme="light"])' in _css()


def test_the_two_dark_blocks_define_identical_tokens():
    """Plain CSS cannot share a block across a media query, so they are
    duplicated. This is the guard that stops them drifting apart."""
    system_dark = _tokens(_block(':root:not([data-theme="light"])'))
    forced_dark = _tokens(_block(':root[data-theme="dark"]'))

    assert system_dark == forced_dark, (
        "the media-query dark tokens and the [data-theme=dark] tokens differ: "
        f"{set(system_dark.items()) ^ set(forced_dark.items())}"
    )


# ------------------------------------------------------------------ contrast

TEXT_PAIRS = [
    ("ink", "paper"),
    ("ink", "surface"),
    ("muted", "paper"),
    ("muted", "surface"),
    ("credit", "surface"),
    ("debit", "surface"),
]

FILLS = ["action", "credit-fill", "debit-fill", "info-fill"]


@pytest.mark.parametrize("foreground,background", TEXT_PAIRS)
def test_light_text_meets_aa(light, foreground, background):
    ratio = contrast(_resolve(foreground, light, {}), _resolve(background, light, {}))
    assert ratio >= 4.5, f"--{foreground} on --{background} is {ratio:.2f}:1"


@pytest.mark.parametrize("foreground,background", TEXT_PAIRS)
def test_dark_text_meets_aa(dark, foreground, background):
    ratio = contrast(_resolve(foreground, dark, {}), _resolve(background, dark, {}))
    assert ratio >= 4.5, f"--{foreground} on --{background} is {ratio:.2f}:1 (dark)"


@pytest.mark.parametrize("fill", FILLS)
def test_black_text_on_every_fill_meets_aa(light, fill):
    """Fills always carry black text, in both themes. One check covers both."""
    ratio = contrast("#0a0a0a", _resolve(fill, light, {}))
    assert ratio >= 4.5, f"black on --{fill} is {ratio:.2f}:1"


def test_the_action_colour_is_neither_green_nor_red(light):
    """It must not compete with the owed/owe signal."""
    action = _resolve("action", light, {})
    red, green, blue = (int(action.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

    dominant_green = green > red + 30 and green > blue + 30
    dominant_red = red > green + 30 and red > blue + 30
    assert not dominant_green, f"{action} reads as green, same as 'you are owed'"
    assert not dominant_red, f"{action} reads as red, same as 'you owe'"


def test_owed_and_owe_are_clearly_different_colours(light):
    owed, owe = _resolve("credit-fill", light, {}), _resolve("debit-fill", light, {})
    assert contrast(owed, owe) > 1.4, "the money pair is too close to tell apart"


# -------------------------------------------------------------- the toggle


def test_every_entry_template_applies_the_theme_before_paint():
    """A deferred script would paint the wrong theme first, then correct it."""
    for name in ["templates/base.html"] + STANDALONE_TEMPLATES:
        body = (Path(settings.BASE_DIR) / name).read_text(encoding="utf-8")
        assert "flatsplit-theme" in body, f"{name} never reads the saved theme"
        head = body[: body.index("</head>")]
        assert "flatsplit-theme" in head, f"{name} applies the theme after </head>"


@pytest.mark.django_db
def test_the_dashboard_offers_a_theme_toggle(client, django_user_model):
    django_user_model.objects.create_user(username="anuj", password="x")
    client.login(username="anuj", password="x")

    body = client.get(reverse("core:dashboard")).content.decode()

    assert 'data-theme-toggle' in body
    assert "aria-label" in body


@pytest.mark.django_db
def test_the_toggle_is_a_real_button_not_a_bare_div(client, django_user_model):
    django_user_model.objects.create_user(username="anuj", password="x")
    client.login(username="anuj", password="x")

    body = client.get(reverse("core:dashboard")).content.decode()
    index = body.index("data-theme-toggle")

    assert body.rfind("<button", 0, index) > body.rfind("<div", 0, index)
