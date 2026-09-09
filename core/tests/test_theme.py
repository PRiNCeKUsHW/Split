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
    """app.css with /* comments */ removed.

    Structural assertions must not trip over prose: a comment explaining why
    translateX was avoided still contains the word "translateX".
    """
    return re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)


def _blocks(selector: str) -> list[str]:
    """Bodies of every rule using this selector. A selector may appear more
    than once -- .nav-add .fab has both a colour rule and a layout rule."""
    text, bodies, cursor = _css(), [], 0
    while True:
        index = text.find(selector, cursor)
        if index == -1:
            return bodies
        start = text.index("{", index) + 1
        depth, scan = 1, start
        while depth:
            depth += {"{": 1, "}": -1}.get(text[scan], 0)
            scan += 1
        bodies.append(text[start : scan - 1])
        cursor = scan


def _block(selector: str) -> str:
    """The first rule body for this selector."""
    return _blocks(selector)[0]


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


# ------------------------------------------------------------- bottom nav


def _fab_layout() -> str:
    """The .nav-add .fab rule that actually positions it."""
    for body in _blocks(".nav-add .fab {"):
        if "position: absolute" in body:
            return body
    raise AssertionError("no .nav-add .fab rule positions the button")


def test_the_add_button_is_explicitly_centred():
    """position:absolute with no `left` falls back to the static position,
    which inside a flex container is not reliably centred."""
    block = _fab_layout()

    assert "left: 50%" in block, "the raised add button has no horizontal anchor"
    assert "margin-left: -28px" in block, "half its own width, to centre it"


def test_the_add_button_sits_above_the_bar():
    assert "top: -22px" in _fab_layout()


def test_the_add_button_keeps_transform_for_its_press_state():
    """Centring with translateX would be overwritten by the press animation."""
    assert "translateX" not in _fab_layout()
    assert "transform: translate(" in _block(".nav-add:active .fab")


def test_the_nav_label_rule_excludes_the_fab():
    """The fab is a <span>; a bare `.nav-add span` rule sinks it into the bar."""
    css = _css()

    assert ".nav-add > span:not(.fab)" in css
    assert "\n.nav-add span {" not in css, "bare span rule still matches the fab"
