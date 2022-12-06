import asyncio
import json
import os
import random
import sys
from logging import getLogger, Logger
from logging.config import dictConfig
from pathlib import Path
from typing import NamedTuple, Optional

import click
import colorama
from dotenv import dotenv_values

import click_utils
from add import add_images
from run import run_bot
from settings import LOG_CONFIG_FILE_PATH_FMT


class TgGroup(NamedTuple):
    chat_id: int
    thread_id: Optional[int] = None


def init_logging(work_dir: Path):
    logs_path = work_dir / 'logs'
    logs_path.mkdir(parents=True, exist_ok=True)
    log_config_path = LOG_CONFIG_FILE_PATH_FMT.format('_debug' if __debug__ else '')
    with open(log_config_path) as file:
        config = json.load(file)
        if file_handler := config['handlers'].get('FileHandler'):
            file_handler['filename'] = str(logs_path / 'log.txt')
        dictConfig(config)


@click.group(invoke_without_command=True)
@click.option('--work_dir', '-wd', type=Path, default=None)
@click.pass_context
def command_group(context, work_dir: Path):
    environment = os.environ if not __debug__ else dotenv_values(".env")
    work_dir = work_dir or Path(environment.get('WORK_DIR') or 'user_data')
    init_logging(work_dir)
    context.obj['logger'] = getLogger('main')
    context.obj['environment'] = environment
    context.obj['work_dir'] = work_dir
    if not work_dir.exists():
        work_dir.mkdir()
    if context.invoked_subcommand is None:
        context.invoke(command_run)


@command_group.command(name='run')
@click.pass_context
@click.option('--token', '-t', type=str, default=None)
@click.option('--groups', '-gs', multiple=True, type=str, default=[])
@click_utils.log_work_process('main')
def command_run(context, token: str, groups: list[str]):
    work_dir: Path = context.obj['work_dir']
    logger: Logger = context.obj['logger']
    token = token or context.obj['environment'].get('TOKEN')
    if not groups:
        if groups_from_env := context.obj['environment'].get('GROUPS'):
            groups = groups_from_env.split(',')
    if token is None:
        raise RuntimeError('The api token is not specified!')
    groups = frozenset((TgGroup(*map(int, s.split('/'))) for s in groups))
    asyncio.run(run_bot(token, groups, work_dir, logger))


@command_group.command(name='add')
@click.pass_context
@click.argument('source', type=click.Path(exists=True), required=True)
@click.option('--generate_test', '-gt', is_flag=True, default=False)
@click_utils.log_work_process('main')
def command_add(context, source: str, generate_test: bool):
    work_dir: Path = context.obj['work_dir']
    logger: Logger = context.obj['logger']
    images_path = work_dir / 'background_images'
    images_path.mkdir(parents=True, exist_ok=True)
    add_images(Path(source), images_path, generate_test, logger)


def startup():
    colorama.init()
    random.seed()

    if sys.platform.startswith('win'):
        from win_console_utils import init_win_console

        init_win_console()
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    command_group.main(obj={}, standalone_mode=False)


if __name__ == '__main__':
    startup()
