import asyncio
import random
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from logging import Logger
from pathlib import Path
from typing import NamedTuple, BinaryIO, Optional

from PIL import Image
from aiogram import Dispatcher, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, Text
from aiogram.types import Message, BufferedInputFile, PhotoSize, UserProfilePhotos

from image_utils import generate_image


class TgGroup(NamedTuple):
    chat_id: int
    thread_id: Optional[int] = None


async def run_bot(token: str,
                  groups: frozenset[TgGroup],
                  work_dir: Path,
                  logger: Logger):
    bot = Bot(token=token)
    context = dict(
        groups=groups,
        work_dir=work_dir,
        bot=bot,
        logger=logger,
        storage={},
    )
    dp = Dispatcher()
    dp.message.register(on_quote, Command('quote', 'q'))
    dp.message.register(on_quote, Text(text=('q', 'Q', 'Ц', 'ц')))
    dp.message.register(on_delete, Command('delete', 'del', 'd'))
    with ThreadPoolExecutor(max_workers=2) as executor:
        context['executor'] = executor
        context['loop'] = asyncio.get_event_loop()
        await dp.start_polling(bot, context=context)


async def on_quote(message: Message, context: dict):
    logger: Logger = context['logger']
    thread_id = message.message_thread_id if message.is_topic_message else None

    logger.debug(f'/quote {message.chat.id=} {thread_id=} {message.message_id=}')

    groups: frozenset[TgGroup] = context['groups']
    logger.debug(f'{groups=}')
    if groups and TgGroup(message.chat.id, thread_id) not in groups:
        return

    bot, loop, executor = context['bot'], context['loop'], context['executor']
    work_dir: Path = context['work_dir']

    if message.reply_to_message and message.reply_to_message.text:
        photo_data = await get_photo_data(bot, message.reply_to_message.from_user.id)

        logger.debug('generation ...')
        images_path = work_dir / 'background_images'
        background_images = [path for path in images_path.glob('*.jpeg')
                             if not path.stem.endswith('_test')]
        background_file_path = random.choice(background_images)
        args = message.reply_to_message, photo_data, background_file_path
        buffered_input_file = await loop.run_in_executor(executor, generation_task, *args)

        logger.debug('finished.')
        await bot.send_photo(chat_id=message.chat.id,
                             message_thread_id=thread_id,
                             photo=buffered_input_file)
        try:
            await message.delete()
        except TelegramBadRequest:
            pass


async def on_delete(message: Message, context: dict):
    logger: Logger = context['logger']
    if is_reply(message):
        bot = context['bot']
        if message.reply_to_message.from_user.id == bot.id:
            message_id = message.reply_to_message.message_id
            logger.debug(f'/del {message_id}')
            await bot.delete_message(message.chat.id, message_id)
            try:
                await message.delete()
            except TelegramBadRequest:
                pass


def generation_task(message: Message,
                    photo_data: Optional[BinaryIO],
                    background_file_path: Path) -> BufferedInputFile:
    with Image.open(background_file_path) as background_image:
        user = message.from_user
        image = generate_image(user.username,
                               user.first_name,
                               user.last_name,
                               message.text,
                               photo_data,
                               background_image)
        bytes_io = BytesIO()
        image.save(bytes_io, "JPEG")
        return BufferedInputFile(file=bytes_io.getvalue(), filename='')


def is_reply(message: Message) -> bool:
    if message.is_topic_message:
        return message.reply_to_message and \
               message.reply_to_message.message_id != message.message_thread_id

    return message.reply_to_message is not None


def get_biggest_sqr_photo(photos: list[list[PhotoSize]]) -> Optional[PhotoSize]:
    if photos:
        photo_with_max_size: Optional[PhotoSize] = None
        for pp in photos:
            for p in pp:
                if p.width == p.height:
                    if not photo_with_max_size:
                        photo_with_max_size = p
                    elif photo_with_max_size.width > p.width:
                        photo_with_max_size = p
        return photo_with_max_size
    return None


async def get_photo_data(bot: Bot, user_id: int) -> Optional[BinaryIO]:
    user_profile_photo: UserProfilePhotos = await bot.get_user_profile_photos(user_id)
    if photo := get_biggest_sqr_photo(user_profile_photo.photos):
        file = await bot.get_file(photo.file_id)
        return await bot.download(file)
    return None
