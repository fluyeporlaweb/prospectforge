"""Generate the prospectforge banner and architecture diagrams.

The script uses Pillow and a handful of system fonts with DejaVu fallbacks.
Install Pillow first (`pip install pillow`), then run it from the repository root:

    python scripts/generate_assets.py

Outputs:
    assets/banner.png        1280x640
    assets/architecture.png  1280x720
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BG = "#0B1220"
PANEL = "#151C2C"
BORDER = "#2A3348"
ACCENT = "#3EE0C5"
SECONDARY = "#7AA2FF"
TEXT = "#F4F7FB"
MUTED = "#9AA6B2"

FONT_DIRS = [
    Path("/usr/share/fonts/truetype/sand-box/custom/Open Sauce Sans"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype"),
]

FONT_FILES = {
    "regular": [
        "OpenSauceSans-Regular.ttf",
        "DejaVuSans.ttf",
    ],
    "medium": [
        "OpenSauceSans-Medium.ttf",
        "OpenSauceSans-Regular.ttf",
        "DejaVuSans.ttf",
    ],
    "semibold": [
        "OpenSauceSans-SemiBold.ttf",
        "OpenSauceSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ],
    "bold": [
        "OpenSauceSans-Bold.ttf",
        "OpenSauceSans-SemiBold.ttf",
        "DejaVuSans-Bold.ttf",
    ],
    "extrabold": [
        "OpenSauceSans-ExtraBold.ttf",
        "OpenSauceSans-Black.ttf",
        "OpenSauceSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ],
}


def _find_font(weight: str) -> Path:
    for directory in FONT_DIRS:
        for filename in FONT_FILES[weight]:
            candidate = directory / filename
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"No usable font found for weight {weight!r}")


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_find_font(weight)), size=size)


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: str,
    tracking: float,
) -> float:
    x, y = xy
    start = x
    for char in text:
        draw.text((x, y), char, font=text_font, fill=fill, anchor="lt")
        x += draw.textlength(char, font=text_font) + tracking
    return x - start - tracking


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    text_font: ImageFont.FreeTypeFont,
    max_width: float,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=text_font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    x1: float,
    x2: float,
    y: float,
    color: str,
    width: int = 3,
) -> None:
    head = 11
    draw.line((x1, y, x2 - head, y), fill=color, width=width)
    draw.polygon(
        [(x2, y), (x2 - head, y - 7), (x2 - head, y + 7)],
        fill=color,
    )


def draw_banner() -> Image.Image:
    width, height = 1280, 640
    image = Image.new("RGB", (width, height), rgb(BG))
    draw = ImageDraw.Draw(image)
    margin = 88

    label_font = font(18, "semibold")
    draw_tracked(
        draw,
        (margin, 112),
        "OPEN-SOURCE B2B LEAD PIPELINE",
        label_font,
        ACCENT,
        tracking=1.4,
    )

    title_font = font(86, "extrabold")
    draw.text((margin, 150), "prospectforge", font=title_font, fill=TEXT, anchor="lt")

    draw.rounded_rectangle(
        (margin, 284, margin + 132, 290),
        radius=3,
        fill=ACCENT,
    )

    hook_font = font(32, "bold")
    draw.text(
        (margin, 318),
        "Discover. Qualify. Draft. Never auto-send.",
        font=hook_font,
        fill=TEXT,
        anchor="lt",
    )

    description_font = font(21, "regular")
    draw.text(
        (margin, 376),
        "Apify-backed discovery. ICP qualification with written reasons. Drafts only.",
        font=description_font,
        fill=MUTED,
        anchor="lt",
    )

    chip_top = 462
    chip_height = 104
    gap = 32
    chip_width = (width - 2 * margin - gap * 3) / 4
    stages = [
        ("01", "Discover", "Apify Actor"),
        ("02", "Qualify", "LLM / heuristic"),
        ("03", "Draft", "Personalized message"),
        ("04", "Export", "JSON / CSV"),
    ]
    number_font = font(15, "semibold")
    stage_font = font(25, "semibold")
    stage_sub_font = font(15, "regular")

    for index, (number, label, subtitle) in enumerate(stages):
        x = margin + index * (chip_width + gap)
        draw.rounded_rectangle(
            (x, chip_top, x + chip_width, chip_top + chip_height),
            radius=16,
            fill=rgb(PANEL),
            outline=rgb(BORDER),
            width=2,
        )
        draw_tracked(
            draw,
            (x + 22, chip_top + 18),
            number,
            number_font,
            ACCENT,
            tracking=1.4,
        )
        draw.text(
            (x + 22, chip_top + 42),
            label,
            font=stage_font,
            fill=TEXT,
            anchor="lt",
        )
        draw.text(
            (x + 22, chip_top + 76),
            subtitle,
            font=stage_sub_font,
            fill=MUTED,
            anchor="lt",
        )
        if index < len(stages) - 1:
            arrow_y = chip_top + chip_height / 2
            draw_arrow(
                draw,
                x + chip_width + 7,
                x + chip_width + gap - 7,
                arrow_y,
                ACCENT,
                width=2,
            )

    return image


def draw_architecture() -> Image.Image:
    width, height = 1280, 720
    image = Image.new("RGB", (width, height), rgb(BG))
    draw = ImageDraw.Draw(image)
    margin = 48

    title_font = font(42, "extrabold")
    draw.text(
        (margin, 44),
        "prospectforge pipeline",
        font=title_font,
        fill=TEXT,
        anchor="lt",
    )

    subtitle_font = font(19, "regular")
    draw.text(
        (margin, 104),
        "Discover contacts, qualify against your ICP, draft outreach, export locally.",
        font=subtitle_font,
        fill=MUTED,
        anchor="lt",
    )

    box_top = 214
    box_height = 258
    gap = 60
    box_width = (width - 2 * margin - gap * 3) / 4
    stages = [
        (
            "01",
            "Discover",
            "Apify Actor",
            "B2B contacts with live emails, normalized into one Lead model.",
        ),
        (
            "02",
            "Qualify",
            "LLM / heuristic",
            "A 0-100 fit score plus written reasons you can inspect and tune.",
        ),
        (
            "03",
            "Draft",
            "Personalized message",
            "Subject and body for every lead above your score threshold.",
        ),
        (
            "04",
            "Export",
            "JSON / CSV",
            "Local leads, drafts, and flat CSVs under out/. Nothing is sent.",
        ),
    ]
    number_font = font(15, "semibold")
    stage_font = font(29, "semibold")
    stage_sub_font = font(17, "medium")
    body_font = font(16, "regular")
    arrow_label_font = font(16, "medium")
    arrow_labels = ["leads", "scores", "drafts"]

    for index, (number, label, subtitle, body) in enumerate(stages):
        x = margin + index * (box_width + gap)
        draw.rounded_rectangle(
            (x, box_top, x + box_width, box_top + box_height),
            radius=20,
            fill=rgb(PANEL),
            outline=rgb(BORDER),
            width=2,
        )
        draw_tracked(
            draw,
            (x + 24, box_top + 20),
            number,
            number_font,
            ACCENT,
            tracking=1.4,
        )
        draw.text(
            (x + 24, box_top + 44),
            label,
            font=stage_font,
            fill=TEXT,
            anchor="lt",
        )
        draw.text(
            (x + 24, box_top + 86),
            subtitle,
            font=stage_sub_font,
            fill=SECONDARY,
            anchor="lt",
        )
        draw.line(
            (x + 24, box_top + 120, x + box_width - 24, box_top + 120),
            fill=rgb(BORDER),
            width=2,
        )
        body_lines = wrap_text(draw, body, body_font, box_width - 48)
        body_y = box_top + 138
        for line in body_lines:
            draw.text(
                (x + 24, body_y),
                line,
                font=body_font,
                fill=MUTED,
                anchor="lt",
            )
            body_y += 24

        if index < len(stages) - 1:
            arrow_y = box_top + box_height / 2
            draw_arrow(
                draw,
                x + box_width + 9,
                x + box_width + gap - 9,
                arrow_y,
                ACCENT,
                width=3,
            )
            label_text = arrow_labels[index]
            label_width = draw.textlength(label_text, font=arrow_label_font)
            draw.text(
                (
                    x + box_width + (gap - label_width) / 2,
                    arrow_y - 34,
                ),
                label_text,
                font=arrow_label_font,
                fill=MUTED,
                anchor="lt",
            )

    footer_top = 552
    footer_height = 96
    draw.rounded_rectangle(
        (margin, footer_top, width - margin, footer_top + footer_height),
        radius=16,
        fill=rgb(PANEL),
        outline=rgb(BORDER),
        width=2,
    )
    draw.rounded_rectangle(
        (margin + 28, footer_top + 26, margin + 34, footer_top + 70),
        radius=3,
        fill=ACCENT,
    )
    footer_font = font(20, "semibold")
    footer_sub_font = font(16, "regular")
    draw.text(
        (margin + 52, footer_top + 22),
        "Dry-run by default. Never sends email. Works offline with fixtures.",
        font=footer_font,
        fill=TEXT,
        anchor="lt",
    )
    draw.text(
        (margin + 52, footer_top + 56),
        "Live Apify discovery runs only with --live and APIFY_TOKEN.",
        font=footer_sub_font,
        fill=MUTED,
        anchor="lt",
    )

    return image


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    banner = draw_banner()
    architecture = draw_architecture()

    assert banner.size == (1280, 640)
    assert architecture.size == (1280, 720)

    banner.save(ASSETS / "banner.png", format="PNG", optimize=True)
    architecture.save(ASSETS / "architecture.png", format="PNG", optimize=True)
    print(f"Wrote {ASSETS / 'banner.png'} ({banner.width}x{banner.height})")
    print(f"Wrote {ASSETS / 'architecture.png'} ({architecture.width}x{architecture.height})")


if __name__ == "__main__":
    main()
