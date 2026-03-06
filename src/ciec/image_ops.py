# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance, UnidentifiedImageError

from .constants import FIXED_TARGET
from .utils import safe_unique_path


def mean_luminance_rgb(im_rgb: Image.Image) -> float:
    g = im_rgb.convert("L")
    hist = g.histogram()
    total = sum(hist)
    if total == 0:
        return 0.0
    s = 0
    for i, c in enumerate(hist):
        s += i * c
    return s / total


def auto_brightness(im_rgb: Image.Image) -> tuple[Image.Image, str]:
    im2 = ImageOps.autocontrast(im_rgb, cutoff=1)
    m = mean_luminance_rgb(im2)

    if m < 80:
        b, c = 1.35, 1.10
    elif m < 110:
        b, c = 1.18, 1.06
    elif m > 185:
        b, c = 0.92, 1.02
    else:
        b, c = 1.00, 1.03

    tag = f"auto_bright:mean={m:.1f},B={b:.2f},C={c:.2f}"
    im3 = ImageEnhance.Brightness(im2).enhance(b)
    im4 = ImageEnhance.Contrast(im3).enhance(c)
    return im4, tag


def convert_cover(
    src: Path,
    dst: Path,
    quality: int,
    do_autobright: bool,
    dry_run: bool,
) -> tuple[bool, str, str, Path]:
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode != "RGB":
                im = im.convert("RGB")

            adjust_info = "auto_bright:off"
            if do_autobright:
                im, adjust_info = auto_brightness(im)

            out = ImageOps.fit(
                im,
                FIXED_TARGET,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )

            dst.parent.mkdir(parents=True, exist_ok=True)
            dst_final = safe_unique_path(dst)

            if dry_run:
                return True, "TESTE (não gerou arquivo)", adjust_info, dst_final

            out.save(dst_final, format="JPEG", quality=quality, optimize=True)
            return True, "OK", adjust_info, dst_final

    except UnidentifiedImageError:
        return False, "SKIP: não é imagem", "n/a", dst
    except Exception as e:
        return False, f"ERRO: {e}", "n/a", dst