import random
import textwrap
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO, Optional, Iterable

import emoji
from PIL import Image, ImageDraw, ImageFont

from settings import LABEL_FONT_K, TEXT_FONT_K, PART_K, PHOTO_K, MAX_LINE_WIDTH, MAX_LINE_COUNT

COLORS = ('red', 'blue', 'green', 'yellow', 'magenta', 'pink', 'lime')
FONT_NAME = 'fonts/arial.ttf'


@dataclass
class Rect:
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    width = property(lambda self: self.right - self.left)
    height = property(lambda self: self.bottom - self.top)

    def to_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom

    def cx(self):
        return self.left + self.width // 2

    def cy(self):
        return self.top + self.height // 2

    def center(self) -> tuple[int, int]:
        return self.cx(), self.cy()


def draw_text_in_center(text: str, font: ImageFont, target_rect: Rect, draw: ImageDraw,
                        align='center',
                        anchor=None):
    box_rect = Rect(*draw.multiline_textbbox((0, 0), text, font=font))
    cx, cy = target_rect.center()
    dx, dy = box_rect.center()
    r = cx - dx, cy - dy, cx - dx + box_rect.width, cy - dy + box_rect.height
    draw.multiline_text(r, text, align=align, anchor=anchor, fill='white', font=font)


def generate_initials(names: Iterable[str]):
    names = map(lambda name: emoji.replace_emoji(name, replace='').strip(), names)
    return "".join((name[0] for name in names if name))


def create_fictive_photo(first_name: str, last_name: str, photo_width: int) -> Image.Image:
    color = random.choice(COLORS)
    photo_image = Image.new('RGB', (photo_width, photo_width), color=color)
    initials = generate_initials((first_name, last_name))
    if initials:
        photo_draw = ImageDraw.Draw(photo_image)
        photo_font = ImageFont.truetype(FONT_NAME, size=int(0.5 * photo_width))
        photo_rect = Rect(0, 0, photo_width, photo_width)
        draw_text_in_center(initials, photo_font, photo_rect, photo_draw, align='center')
    return photo_image


def make_cycle_mask(size) -> Image.Image:
    mask_image = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(mask_image)
    mask_draw.ellipse((0, 0, *size), fill='white', outline='white')
    return mask_image


def draw_left_part(username: str,
                   photo_image: Image.Image,
                   rect: Rect,
                   font: ImageFont,
                   draw: ImageDraw,
                   background_image: Image.Image):
    username = '\n'.join(textwrap.wrap(username, width=20))
    label = f'@{username}\n{datetime.now():%Y-%m-%d %H:%M}'
    label_rect = Rect(*draw.multiline_textbbox((0, 0), label, font=font))

    dx = photo_image.size[0] // 2
    dy = (photo_image.size[1] + label_rect.height) // 2

    cx, cy = rect.center()
    photo_rect = Rect(cx - dx, cy - dy, cx + dx, cy + dy)

    background_image.paste(photo_image,
                           (photo_rect.left, photo_rect.top),
                           make_cycle_mask(photo_image.size))

    label_pos = photo_rect.cx() - label_rect.cx(), photo_rect.bottom + label_rect.top
    draw.multiline_text(label_pos, label, align='center', fill='white', font=font)


def draw_right_part(text: str,
                    max_line_width: int,
                    max_line_count: int,
                    rect: Rect,
                    font: ImageFont,
                    draw: ImageDraw):
    lines = textwrap.wrap(emoji.replace_emoji(text, ' ').strip(),
                          width=max_line_width)
    if len(lines) > max_line_count:
        lines = lines[:max_line_count - 1]
        lines.append('...'.center(max_line_width))
    message_text = '\n'.join(lines)
    draw_text_in_center(message_text, font, rect, draw, align='left')


def generate_image(username: str, first_name: str, last_name: str,
                   message_text: str,
                   photo_data: Optional[BinaryIO],
                   background_image: Image.Image) -> Image.Image:
    w, h = background_image.size

    left_part_width = int(PART_K * w)
    text_font_size = int(TEXT_FONT_K * h)
    text_font = ImageFont.truetype(FONT_NAME, size=text_font_size)
    label_font = ImageFont.truetype(FONT_NAME, size=int(LABEL_FONT_K * text_font_size))

    draw = ImageDraw.Draw(background_image)

    left_rect = Rect(0, 0, left_part_width, h)
    right_rect = Rect(left_part_width, 0, w, h)

    photo_width = int(PHOTO_K * background_image.size[0])
    if photo_data:
        photo_image = Image.open(photo_data)
        photo_image = photo_image.resize((photo_width, photo_width),
                                         Image.Resampling.LANCZOS)
    else:
        photo_image = create_fictive_photo(first_name, last_name, photo_width)

    draw_left_part(username, photo_image, left_rect, label_font, draw, background_image)
    draw_right_part(message_text,
                    MAX_LINE_WIDTH,
                    MAX_LINE_COUNT,
                    right_rect,
                    text_font,
                    draw)
    return background_image


def test():
    import time

    with Image.open('user_data/background_images/background_min.jpeg') as background_image:
        text = " ".join((f"word{i}" for i in range(30)))

        t = time.monotonic()
        image = generate_image('Test', 'Test', 'Test', text, None, background_image)
        print('time:', time.monotonic() - t)

        image.show()


if __name__ == '__main__':
    test()
