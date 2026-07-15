#!/usr/bin/env python3
"""Capture a bounded primary-source figure into an article bundle.

Run this tool through ``uv run --group figure-capture`` after bootstrapping the
repository's optional capture dependencies. It deliberately knows nothing about
article prose or source policy: the writer must still choose an exact primary
figure, describe it accurately, and cite the document in the figure caption.
"""

import argparse
import asyncio
import io
import pathlib
import urllib.request

import fitz
from PIL import Image
from playwright.async_api import async_playwright

MAX_EDGE = 2400
FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}


def output_path(value: str) -> pathlib.Path:
    path = pathlib.Path(value)
    if path.suffix.lower() not in FORMATS:
        raise argparse.ArgumentTypeError(
            "output must end in .png, .jpg, .jpeg, or .webp"
        )
    return path


def normalize(image: Image.Image, output: pathlib.Path) -> None:
    image.thumbnail((MAX_EDGE, MAX_EDGE))
    output.parent.mkdir(parents=True, exist_ok=True)
    if FORMATS[output.suffix.lower()] == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.save(output, format=FORMATS[output.suffix.lower()])


def capture_image(url: str, output: pathlib.Path) -> None:
    with urllib.request.urlopen(url) as response:
        raw = response.read()
    with Image.open(io.BytesIO(raw)) as image:
        normalize(image, output)


def parse_clip(value: str) -> fitz.Rect:
    try:
        x, y, width, height = (float(part) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("clip must be x,y,width,height") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("clip width and height must be positive")
    return fitz.Rect(x, y, x + width, y + height)


def capture_pdf(
    pdf: pathlib.Path, *, page_number: int, clip: fitz.Rect, output: pathlib.Path
) -> None:
    with fitz.open(pdf) as document:
        page = document[page_number - 1]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False)
    with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
        normalize(image, output)


async def capture_web(url: str, *, selector: str, output: pathlib.Path) -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 1600})
        await page.goto(url, wait_until="networkidle")
        locator = page.locator(selector)
        await locator.scroll_into_view_if_needed()
        await locator.screenshot(path=str(output))
        await browser.close()
    with Image.open(output) as image:
        normalize(image, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    image = commands.add_parser("image", help="download an exact source image")
    image.add_argument("url")
    image.add_argument("output", type=output_path)

    pdf = commands.add_parser("pdf", help="rasterize a precise region of a PDF page")
    pdf.add_argument("file", type=pathlib.Path)
    pdf.add_argument("output", type=output_path)
    pdf.add_argument(
        "--page", type=int, required=True, help="one-based PDF page number"
    )
    pdf.add_argument(
        "--clip", type=parse_clip, required=True, help="x,y,width,height in PDF points"
    )

    web = commands.add_parser(
        "web", help="screenshot one source-page element or canvas"
    )
    web.add_argument("url")
    web.add_argument("output", type=output_path)
    web.add_argument(
        "--selector", required=True, help="CSS selector for the exact figure"
    )

    args = parser.parse_args()
    if args.command == "image":
        capture_image(args.url, args.output)
    elif args.command == "pdf":
        capture_pdf(
            args.file, page_number=args.page, clip=args.clip, output=args.output
        )
    else:
        asyncio.run(capture_web(args.url, selector=args.selector, output=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
