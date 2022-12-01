from logging import Logger
from pathlib import Path

from PIL.Image import Image

from image_utils import generate_image
from settings import BG_IMAGE_SIZE

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')
WORD_COUNT = 30


def add_images(source: Path, dest_dir_path: Path, generate_test: bool, logger: Logger):
    if source.is_file():
        paths = [source, ]
    else:
        paths = [p for p in source.rglob('*')]

    for path in paths:
        if path.suffix in IMAGE_EXTENSIONS:
            logger.debug(path.relative_to(source))
            with Image.open(path) as image:
                new_image = image.resize(BG_IMAGE_SIZE, Image.Resampling.LANCZOS)
                new_image.save(dest_dir_path / path.with_suffix('.jpeg').name, "JPEG")
                if generate_test:
                    text = " ".join((f"word{i}" for i in range(WORD_COUNT)))
                    new_image = generate_image('Test', 'Test', 'Test', text, None, new_image)
                    name = path.with_name(path.stem + '_test').with_suffix('.jpeg').name
                    new_image.save(dest_dir_path / name, "JPEG")
