import os
from PIL import Image, ImageDraw, ImageFont

res_dir = 'mobile/android/app/src/main/res'
densities = {
    'mipmap-mdpi': (48, 108),
    'mipmap-hdpi': (72, 162),
    'mipmap-xhdpi': (96, 216),
    'mipmap-xxhdpi': (144, 324),
    'mipmap-xxxhdpi': (192, 432),
}

bg_color = (167, 139, 250, 255)   # #A78BFA Violet
lime_color = (190, 242, 100, 255) # #BEF264 Electric Lime
ink_color = (10, 10, 10, 255)     # #0A0A0A Deep Ink

def make_legacy_icon(size: int, round_icon: bool = False) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    border = max(2, int(s * 0.045))

    if round_icon:
        d.ellipse([0, 0, s - 1, s - 1], fill=bg_color)
        d.ellipse([0, 0, s - 1, s - 1], outline=ink_color, width=border)
    else:
        radius = int(s * 0.20)
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=bg_color)
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, outline=ink_color, width=border)

    # Inner badge
    badge_w = int(s * 0.58)
    badge_h = int(s * 0.58)
    shadow = int(s * 0.045)
    
    bx = (s - badge_w) // 2
    by = (s - badge_h) // 2

    # Drop shadow
    d.rectangle([bx + shadow, by + shadow, bx + badge_w + shadow, by + badge_h + shadow], fill=ink_color)
    # Badge surface
    d.rectangle([bx, by, bx + badge_w, by + badge_h], fill=lime_color, outline=ink_color, width=border)

    # Glyph
    font_size = int(badge_h * 0.75)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', font_size)
    glyph = '\u20b9'
    bbox = d.textbbox((0, 0), glyph, font=font)
    gw = bbox[2] - bbox[0]
    gh = bbox[3] - bbox[1]
    gx = bx + (badge_w - gw) / 2 - bbox[0]
    gy = by + (badge_h - gh) / 2 - bbox[1]
    d.text((gx, gy), glyph, font=font, fill=ink_color)

    return img.resize((size, size), Image.Resampling.LANCZOS)

def make_foreground_icon(fg_size: int) -> Image.Image:
    scale = 4
    s = fg_size * scale
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    border = max(2, int(s * 0.035))

    # Badge in central safe zone (safe zone is middle 66%)
    badge_w = int(s * 0.44)
    badge_h = int(s * 0.44)
    shadow = int(s * 0.035)

    bx = (s - badge_w) // 2
    by = (s - badge_h) // 2

    # Drop shadow
    d.rectangle([bx + shadow, by + shadow, bx + badge_w + shadow, by + badge_h + shadow], fill=ink_color)
    # Badge surface
    d.rectangle([bx, by, bx + badge_w, by + badge_h], fill=lime_color, outline=ink_color, width=border)

    # Glyph
    font_size = int(badge_h * 0.75)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', font_size)
    glyph = '\u20b9'
    bbox = d.textbbox((0, 0), glyph, font=font)
    gw = bbox[2] - bbox[0]
    gh = bbox[3] - bbox[1]
    gx = bx + (badge_w - gw) / 2 - bbox[0]
    gy = by + (badge_h - gh) / 2 - bbox[1]
    d.text((gx, gy), glyph, font=font, fill=ink_color)

    return img.resize((fg_size, fg_size), Image.Resampling.LANCZOS)

for folder, (size, fg_size) in densities.items():
    target_dir = os.path.join(res_dir, folder)
    os.makedirs(target_dir, exist_ok=True)
    
    # Legacy square
    make_legacy_icon(size, round_icon=False).save(os.path.join(target_dir, 'ic_launcher.png'), 'PNG', optimize=True)
    # Legacy round
    make_legacy_icon(size, round_icon=True).save(os.path.join(target_dir, 'ic_launcher_round.png'), 'PNG', optimize=True)
    # Adaptive foreground
    make_foreground_icon(fg_size).save(os.path.join(target_dir, 'ic_launcher_foreground.png'), 'PNG', optimize=True)
    print(f'Generated {folder}: {size}px icon, {fg_size}px foreground')

# Create adaptive xml & colors
anydpi_dir = os.path.join(res_dir, 'mipmap-anydpi-v26')
os.makedirs(anydpi_dir, exist_ok=True)

with open(os.path.join(anydpi_dir, 'ic_launcher.xml'), 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@color/ic_launcher_background"/>\n'
            '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
            '</adaptive-icon>\n')

with open(os.path.join(anydpi_dir, 'ic_launcher_round.xml'), 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@color/ic_launcher_background"/>\n'
            '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
            '</adaptive-icon>\n')

with open(os.path.join(res_dir, 'values', 'colors.xml'), 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n'
            '<resources>\n'
            '    <color name="ic_launcher_background">#A78BFA</color>\n'
            '</resources>\n')

# Also save master 512x512 app icon
make_legacy_icon(512, round_icon=False).save('mobile/app_icon_512.png', 'PNG', optimize=True)
print('All icons generated successfully!')
