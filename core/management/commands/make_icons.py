"""Draw the PWA icons with Pillow so no binary assets need vendoring.

Regenerate after any palette change:  python manage.py make_icons
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

MARIGOLD = (255, 212, 59, 255)
INK = (10, 10, 10, 255)


def _rupee_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Find a font that actually has the rupee glyph, else fall back."""
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_icon(size: int, *, maskable: bool) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    stroke = max(2, int(size * 0.055))

    if maskable:
        # Maskable icons get cropped to a circle by the launcher, so the
        # background must bleed to the edges and the glyph stay in the
        # middle 80%.
        draw.rectangle([0, 0, size, size], fill=MARIGOLD)
        glyph_size = int(size * 0.44)
    else:
        # Neobrutalism: flat fill, hard black border, no rounding.
        draw.rectangle([0, 0, size - 1, size - 1], fill=MARIGOLD,
                       outline=INK, width=stroke)
        glyph_size = int(size * 0.58)

    font = _rupee_font(glyph_size)
    glyph = "\u20b9"
    box = draw.textbbox((0, 0), glyph, font=font)
    draw.text(
        ((size - (box[2] - box[0])) / 2 - box[0], (size - (box[3] - box[1])) / 2 - box[1]),
        glyph,
        font=font,
        fill=INK,
    )
    return img


class Command(BaseCommand):
    help = "Generate the PWA icons into static/icons/."

    def handle(self, *args, **options) -> None:
        out = Path(settings.BASE_DIR) / "static" / "icons"
        out.mkdir(parents=True, exist_ok=True)

        specs = [
            ("icon-192.png", 192, False),
            ("icon-512.png", 512, False),
            ("icon-maskable-512.png", 512, True),
            ("favicon-32.png", 32, False),
        ]
        for name, size, maskable in specs:
            _draw_icon(size, maskable=maskable).save(out / name, "PNG", optimize=True)
            self.stdout.write(self.style.SUCCESS(f"wrote {name} ({size}px)"))
