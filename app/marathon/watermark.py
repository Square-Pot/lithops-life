"""Водяной знак для скачиваемых финальных фото: белый полупрозрачный бейдж марафона + «Marathon YYYY / lithops.life»."""
import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

ASSETS = Path(__file__).resolve().parent / 'assets'
OPACITY = 0.7          # непрозрачность белых элементов
SHADOW_OPACITY = 0.45  # тёмная подложка, чтобы знак читался на светлом фоне
VERSION = 1            # поднять при изменении вида знака — сбросит кэш


@lru_cache(maxsize=1)
def _logo_mask():
    """Линии логотипа как маска: чёрные линии → непрозрачно, светлая заливка и фон → прозрачно."""
    logo = Image.open(ASSETS / 'watermark_logo.png').convert('RGBA')
    darkness = ImageOps.invert(logo.convert('L'))
    return ImageChops.multiply(darkness, logo.getchannel('A'))


def _font(size):
    return ImageFont.truetype(str(ASSETS / 'DejaVuSans-Bold.ttf'), size)


def _paste_white(base, mask, xy, opacity):
    """Кладёт белый цвет по маске с тенью под ним."""
    blur = max(2, mask.width // 60)
    shadow = Image.new('L', base.size, 0)
    shadow.paste(mask, xy)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * SHADOW_OPACITY))
    base.paste(Image.new('RGBA', base.size, (0, 0, 0, 255)), (0, 0), shadow)

    layer = Image.new('L', base.size, 0)
    layer.paste(mask, xy)
    layer = layer.point(lambda v: int(v * opacity))
    base.paste(Image.new('RGBA', base.size, (255, 255, 255, 255)), (0, 0), layer)


def apply(image_bytes, marathon_name, site='lithops.life'):
    photo = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert('RGBA')
    w, h = photo.size
    short = min(w, h)
    margin = int(short * 0.035)

    # бейдж
    size = int(short * 0.16)
    badge = _logo_mask().resize((size, size), Image.LANCZOS)
    bx, by = w - margin - size, h - margin - size
    _paste_white(photo, badge, (bx, by), OPACITY)

    # подпись слева от бейджа, выровнена по его центру
    big, small = _font(int(size * 0.24)), _font(int(size * 0.17))
    lines = [(f'Marathon {marathon_name}' if marathon_name else 'Mesemb Marathon', small), (site, big)]
    gap = int(size * 0.06)
    heights = [f.getbbox(t)[3] for t, f in lines]
    text_h = sum(heights) + gap
    text_w = max(f.getlength(t) for t, f in lines)
    text_mask = Image.new('L', (int(text_w) + 2, text_h + 2), 0)
    draw = ImageDraw.Draw(text_mask)
    y = 0
    for (text, font), line_h in zip(lines, heights):
        draw.text((text_w - font.getlength(text), y), text, font=font, fill=255)  # по правому краю
        y += line_h + gap
    tx = bx - int(size * 0.12) - text_mask.width
    ty = by + (size - text_h) // 2
    _paste_white(photo, text_mask, (tx, ty), OPACITY)

    out = io.BytesIO()
    photo.convert('RGB').save(out, 'JPEG', quality=92)
    return out.getvalue()
