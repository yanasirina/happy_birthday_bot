from consts import API_CATS_URL, POSSIBLE_BUTTONS, BUTTONS
from db_client import DBClient
from keyboards.yes_no_keyboard import question_keyboard, yes_keyboard
from keyboards.dynamic_keyboard import create_inline_kb
from keyboards.numbers_keyboard import keyboard_for_cats
from lexicon.lexicon import LEXICON_RU
from loggers.tg_logger import TgLogger
from loggers.google_sheets_logger import GoogleSheetsLogger
from loggers.logger import Logger

import os
import asyncio
import datetime

import requests
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery
import dotenv

dotenv.load_dotenv()

API_TOKEN: str = os.getenv('BOT_TOKEN')
ADMIN_ID: str = os.getenv('ADMIN_ID')
SHEET_NAME: str = os.getenv('SHEET_NAME')

storage: MemoryStorage = MemoryStorage()

bot: Bot = Bot(token=API_TOKEN)
dp: Dispatcher = Dispatcher(bot, storage=storage)
db_client: DBClient = DBClient()
tg_logger: TgLogger = TgLogger(bot=bot, admin_id=ADMIN_ID)
google_sheets_logger: GoogleSheetsLogger = GoogleSheetsLogger(creds_file="creds.json", sheet_name=SHEET_NAME)
logger: Logger = Logger(tg_logger=tg_logger, google_sheets_logger=google_sheets_logger)


class FSMFillForm(StatesGroup):
    fill_username = State()
    fill_password = State()


class FSMChooseGifts(StatesGroup):
    first_gift = State()
    second_gift = State()
    third_gift = State()


@dp.message_handler(commands=['start', 'help'])
async def process_start_help_commands(message: types.Message):
    await message.answer(text=LEXICON_RU['start_help'])
    if message.text == '/start':
        await logger.tg.log(f'Новый пользователь присоединился к боту\n'
                            f'ID: {message.from_user.id}\n'
                            f'Имя: {message.from_user.full_name}\n'
                            f'Юзернейм: {message.from_user.username}\n')
        await logger.sheets.log(
            current_date=str(datetime.datetime.now()),
            action='start command',
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )


@dp.message_handler(commands=['cat'])
async def process_cat_command(message: types.Message):
    cat_response = requests.get(API_CATS_URL)
    if cat_response.status_code == 200:
        cat_link = cat_response.json()['file']
        await message.answer_photo(cat_link)
    else:
        await message.answer(text=LEXICON_RU['no_cat'])

    await logger.sheets.log(
        current_date=str(datetime.datetime.now()),
        action='cat command',
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )


@dp.message_handler(commands=['login'])
async def process_login_command(message: types.Message):
    await message.answer(text=LEXICON_RU['ask_login'])
    await FSMFillForm.fill_username.set()


async def warning_not_username(message: types.Message):
    await message.answer(text=LEXICON_RU['not_login'])


async def process_username_sent(message: types.Message, state: FSMContext):
    username = message.text
    username_is_correct = db_client.check_username(username)

    if username_is_correct:
        async with state.proxy() as data:
            data['username'] = message.text
        await message.answer(text=LEXICON_RU['good_login'])
        await FSMFillForm.fill_password.set()

    else:
        await message.answer(text=LEXICON_RU['bad_login'])


async def warning_not_password(message: types.Message):
    await message.answer(text=LEXICON_RU['not_password'])


async def process_password_sent(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    username = data['username']
    user_id = db_client.check_password(username, password)

    if user_id:
        if not db_client.is_logged_in(user_id):
            db_client.log_in(user_id, message.chat.id)
            await message.answer(text=LEXICON_RU['good_password'])
            await send_congrats(message, state)

        else:
            await message.answer(text=LEXICON_RU['already_logged_in'])
            await state.finish()

    else:
        await message.answer(text=LEXICON_RU['bad_password'])


async def process_cancel_command(message: types.Message, state: FSMContext):
    await message.answer(text=LEXICON_RU['cancel'])

    await state.reset_state()


async def send_congrats(message: types.Message, state: FSMContext):
    await state.finish()

    await logger.tg.log(f'Новый пользователь авторизовался\n'
                        f'ID: {message.from_user.id}\n'
                        f'Имя: {message.from_user.full_name}\n'
                        f'Юзернейм: {message.from_user.username}\n')

    with open('media/other/first_video.MOV', 'rb') as video:
        await message.answer_video(video)
    await asyncio.sleep(8)

    await message.answer(text=LEXICON_RU['hard_year'], parse_mode='MarkdownV2')
    await asyncio.sleep(5)
    with open('media/other/certificate.jpg', 'rb') as photo:
        await message.answer_photo(photo)

    await asyncio.sleep(1)
    await message.answer(text=LEXICON_RU['start_game'],
                         reply_markup=question_keyboard)


async def process_yes_button_press(callback: CallbackQuery):
    await callback.message.edit_text(text=LEXICON_RU['yes_button'])
    await callback.answer(text=LEXICON_RU['rules'], show_alert=True)
    keyboard = create_inline_kb(1, **BUTTONS)
    await callback.message.edit_reply_markup(keyboard)
    await FSMChooseGifts.first_gift.set()


async def process_no_button_press(callback: CallbackQuery):
    await callback.answer(text=LEXICON_RU['no_button'], show_alert=True)
    await callback.message.edit_reply_markup(yes_keyboard)


async def warning_not_a_gift(message: types.Message):
    await message.answer(text=LEXICON_RU['not_a_gift'])


async def create_keyboard(state: FSMContext):
    data = await state.get_data()

    numbers = data.values()
    btns = {}
    for i in range(1, 10):
        btn_name = 'btn_' + str(i)
        if btn_name not in numbers:
            btns[btn_name] = str(i)
    keyboard = create_inline_kb(1, **btns)

    return keyboard


async def process_first_gift(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['first_gift'] = callback.data

    await callback.answer()
    await callback.message.delete()
    keyboard = await create_keyboard(state)

    gift = data['first_gift'][-1]
    await callback.message.answer(text=f'{LEXICON_RU["chosen_gift"]} {gift}')
    with open(f'media/gift1/{gift}.jpg', 'rb') as photo:
        await callback.message.answer_photo(photo)

    await asyncio.sleep(2)
    await callback.message.answer(text=LEXICON_RU['second_gift'], reply_markup=keyboard)

    await FSMChooseGifts.second_gift.set()


async def process_second_gift(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['second_gift'] = callback.data

    await callback.answer()
    await callback.message.delete()
    keyboard = await create_keyboard(state)

    gift = data['second_gift'][-1]
    await callback.message.answer(text=f'{LEXICON_RU["chosen_gift"]} {gift}')
    with open(f'media/gift2/{gift}.jpg', 'rb') as photo:
        await callback.message.answer_photo(photo)
    await asyncio.sleep(2)
    await callback.message.answer(text=LEXICON_RU['third_gift'], reply_markup=keyboard)

    await FSMChooseGifts.third_gift.set()


async def process_third_gift(callback: CallbackQuery, state: FSMContext):
    gift = callback.data[-1]
    await callback.answer()
    await callback.message.delete()

    await callback.message.answer(text=f'{LEXICON_RU["chosen_gift"]} {gift}')
    with open(f'media/gift3/{gift}.jpg', 'rb') as photo:
        await callback.message.answer_photo(photo)
    await asyncio.sleep(2)

    await give_gifts(callback, state)


async def give_gifts(callback: CallbackQuery, state: FSMContext):
    await state.finish()
    await callback.message.answer(text=LEXICON_RU['congratulations'])

    await logger.tg.log(f'Новый пользователь получил поздравление\n'
                        f'ID: {callback.from_user.id}\n'
                        f'Имя: {callback.from_user.full_name}\n'
                        f'Юзернейм: {callback.from_user.username}\n')

    await asyncio.sleep(1)
    with open(f'media/other/second_video.MOV', 'rb') as video:
        await callback.message.answer_video(video)

    await asyncio.sleep(3)
    await callback.message.answer(text=LEXICON_RU['cats'], reply_markup=keyboard_for_cats)


async def send_cats(callback: CallbackQuery, number_of_cats: str):
    cats_dict = {
        '1': ['3.jpg'],
        '2': ['4.jpg', '3.jpg'],
        '3': ['4.jpg', '3.jpg', '2.jpg'],
        '4': ['4.jpg', '1.jpg', '3.jpg', '2.jpg'],
    }

    list_of_cats = cats_dict[number_of_cats]
    for cat in list_of_cats:
        with open(f'media/cats/{cat}', 'rb') as photo:
            await callback.message.answer_photo(photo)
        await asyncio.sleep(1)


async def process_number_button_press(callback: CallbackQuery):
    button_pressed = callback.data[0]
    await callback.answer()
    await callback.message.delete()

    await send_cats(callback, button_pressed)
    await logger.tg.log(f'Новый пользователь получил котиков\n'
                        f'ID: {callback.from_user.id}\n'
                        f'Имя: {callback.from_user.full_name}\n'
                        f'Юзернейм: {callback.from_user.username}\n')

    await asyncio.sleep(1)
    await callback.message.answer(text=LEXICON_RU['finish'])


@dp.message_handler()
async def log_message(message: types.Message):
    await logger.tg.log(f'Сообщение: {message.text}\n\n'
                        f'ID: {message.from_user.id}\n'
                        f'Имя: {message.from_user.full_name}\n'
                        f'Юзернейм: {message.from_user.username}\n')


dp.register_message_handler(process_cancel_command, commands='cancel', state='*')
dp.register_message_handler(process_username_sent, content_types='text', state=FSMFillForm.fill_username)
dp.register_message_handler(warning_not_username, content_types='any', state=FSMFillForm.fill_username)
dp.register_message_handler(process_password_sent, content_types='text', state=FSMFillForm.fill_password)
dp.register_message_handler(warning_not_password, content_types='any', state=FSMFillForm.fill_password)
dp.register_callback_query_handler(process_yes_button_press, text='yes_button_pressed')
dp.register_callback_query_handler(process_no_button_press, text='no_button_pressed')
dp.register_callback_query_handler(process_first_gift, state=FSMChooseGifts.first_gift, text=POSSIBLE_BUTTONS)
dp.register_callback_query_handler(process_second_gift, state=FSMChooseGifts.second_gift, text=POSSIBLE_BUTTONS)
dp.register_callback_query_handler(process_third_gift, state=FSMChooseGifts.third_gift, text=POSSIBLE_BUTTONS)
dp.register_message_handler(warning_not_a_gift, state=[FSMChooseGifts.first_gift, FSMChooseGifts.second_gift,
                                                       FSMChooseGifts.third_gift], content_types='any')
dp.register_callback_query_handler(process_number_button_press, text=['1_button_pressed', '2_button_pressed',
                                                                      '3_button_pressed', '4_button_pressed'])

if __name__ == '__main__':
    while True:
        try:
            executor.start_polling(dp, skip_updates=True)
        except Exception as error:
            txt = f"{error.__class__}\n{error}\n\n{datetime.datetime.now()}"
            url = f"https://api.telegram.org/bot{API_TOKEN}/sendMessage"
            requests.post(url, params={"text": txt, "chat_id": ADMIN_ID})
