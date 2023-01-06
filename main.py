from consts import API_CATS_URL, POSSIBLE_BUTTONS, BUTTONS
from db_client import DBClient
from keyboards.yes_no_keyboard import question_keyboard, yes_keyboard
from keyboards.dynamic_keyboard import create_inline_kb
from keyboards.numbers_keyboard import keyboard_for_cats

import os
import asyncio

import requests
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery
import dotenv


dotenv.load_dotenv()

# Вместо BOT TOKEN нужно вставить токен вашего бота, полученный у @BotFather
API_TOKEN: str = os.getenv('BOT_TOKEN')

# Инициализируем хранилище (создаем экземпляр класса MemoryStorage)
storage: MemoryStorage = MemoryStorage()

# Создаем объекты бота и диспетчера
bot: Bot = Bot(token=API_TOKEN)
dp: Dispatcher = Dispatcher(bot, storage=storage)
db_client: DBClient = DBClient()


# Cоздаем класс, наследуемый от StatesGroup, для группы состояний нашей FSM
class FSMFillForm(StatesGroup):
    # Создаем экземпляры класса State, последовательно
    # перечисляя возможные состояния, в которых будет находиться
    # бот в разные моменты взаимодействия с пользователем
    fill_username = State()        # Состояние ожидания ввода логина
    fill_password = State()        # Состояние ожидания ввода пароля


# Cоздаем класс, наследуемый от StatesGroup, для группы состояний нашей FSM
class FSMChooseGifts(StatesGroup):
    # Создаем экземпляры класса State, последовательно
    # перечисляя возможные состояния, в которых будет находиться
    # бот в разные моменты взаимодействия с пользователем
    first_gift = State()        # Состояние ожидания ввода логина
    second_gift = State()        # Состояние ожидания ввода пароля
    third_gift = State()


# Этот хэндлер будет срабатывать на команды "/start" и "/help" и отправлять базовую информацию в чат
@dp.message_handler(commands=['start', 'help'])
async def process_start_help_commands(message: types.Message):
    await message.answer('Привет!👋\n\n'
                         'Если ты нашел этот бот, то, наверное, у тебя уже есть логин и пароль. '
                         'Чтобы войти нажми /login\n\n'
                         'Но если ты случайно оказался здесь, я могу отправить тебе картинку с котиками '
                         '(даже не одну)🐱 '
                         'Для этого нажми /cat')


# Этот хэндлер будет срабатывать на команду "/cat" и отправлять картинку с котиком в чат
@dp.message_handler(commands=['cat'])
async def process_cat_command(message: types.Message):
    cat_response = requests.get(API_CATS_URL)
    if cat_response.status_code == 200:
        cat_link = cat_response.json()['file']
        await message.answer_photo(cat_link)
    else:
        await message.answer('Котика нет😿')


# Этот хэндлер будет срабатывать на команду "/login" и аутентифицировать пользователя
@dp.message_handler(commands=['login'])
async def process_login_command(message: types.Message):
    await message.answer('Пожалуйста, отправь мне свой логин')
    # Устанавливаем состояние ожидания ввода логина
    await FSMFillForm.fill_username.set()


# Этот хэндлер будет срабатывать, если во время ввода логина
# будет введено что-то некорректное
async def warning_not_username(message: types.Message):
    await message.answer(text='То, что ты отправил не похоже на логин\n'
                              'Пожалуйста, введи корректный логин\n\n'
                              'Если хочешь прервать заполнение анкеты - отправь команду /cancel')


# Этот хэндлер будет срабатывать, если введено корректный логин
# и переводить в состояние ожидания ввода пароля
async def process_username_sent(message: types.Message, state: FSMContext):
    username = message.text
    username_is_correct = db_client.check_username(username)

    # C помощью менеджера контекста сохраняем введенный
    # в хранилище по ключу "username"
    if username_is_correct:
        async with state.proxy() as data:
            data['username'] = message.text
        await message.answer(text='Спасибо!\n\nА теперь введи пароль')
        # Устанавливаем состояние ожидания ввода возраста
        await FSMFillForm.fill_password.set()

    else:
        await message.answer(text='Кажется, ты ввел неверный логин\n\n'
                                  'Пожалуйста, попробуй еще раз или напиши админу, что все сломалось🤯\n\n'
                                  'Если хочешь прервать заполнение анкеты - отправь команду /cancel')


# Этот хэндлер будет срабатывать, если во время ввода пароля
# будет введено что-то некорректное
async def warning_not_password(message: types.Message):
    await message.answer(text='То, что ты отправил не похоже на пароль\n'
                              'Пожалуйста, введи корректный пароль\n\n'
                              'Если хочешь прервать заполнение анкеты - отправь команду /cancel')


# Этот хэндлер будет срабатывать, если введено корректный пароль
# и переводить в состояние ожидания ввода пароля
async def process_password_sent(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    username = data['username']
    user_id = db_client.check_password(username, password)

    # Проверяем пароль и авторизуем пользователя
    if user_id:
        if not db_client.is_logged_in(user_id):
            db_client.log_in(user_id, message.chat.id)
            await message.answer(text='Спасибо!\n\n'
                                      'Теперь ты авторизован и можешь получить свое поздравление🎉💜')
            await send_congrats(message, state)

        else:
            await message.answer(text='Я вижу, что ты уже авторизовался!\n\n'
                                      'Меня не обмануть😄')
            await state.finish()

    else:
        await message.answer(text='Кажется, ты ввел неверный пароль\n\n'
                                  'Пожалуйста, попробуй еще раз или напиши админу, что все сломалось🤯\n\n'
                                  'Если хочешь прервать заполнение анкеты - отправь команду /cancel')


# Этот хэндлер будет срабатывать на команду "/cancel"
# и отключать машину состояний
async def process_cancel_command(message: types.Message, state: FSMContext):
    await message.answer(text='Вы вышли из машины состояний\n\n'
                              'Чтобы снова перейти к авторизации - '
                              'отправьте команду /login')
    # Сбрасываем состояние
    await state.reset_state()


# Функция, которая отправляет поздравление авторизованному пользователю
async def send_congrats(message: types.Message, state: FSMContext):
    await state.finish()
    with open('media/other/first_video.MOV', 'rb') as video:
        await message.answer_video(video)
    await asyncio.sleep(3)

    await message.answer('Здесь будет текст про трудный год')
    await asyncio.sleep(3)
    await message.answer(text='И чтобы ты не скучал, предлагаю сыграть в небольшую игру. Ты согласен?',
                         reply_markup=question_keyboard)


# Этот хэндлер будет срабатывать на апдейт типа CallbackQuery
# с data 'big_button_1_pressed'
async def process_yes_button_press(callback: CallbackQuery):
    await callback.message.edit_text('Выбери первую цифру"')
    await callback.answer(text='В игре есть 9 номеров, под каждым находится (или не находится) приз.'
                               'Ты можешь выбрать только 3 цифры и надеяться на удачу!',
                          show_alert=True)
    keyboard = create_inline_kb(1, **BUTTONS)
    await callback.message.edit_reply_markup(keyboard)
    await FSMChooseGifts.first_gift.set()


# Этот хэндлер будет срабатывать на апдейт типа CallbackQuery
# с data 'big_button_2_pressed'
async def process_no_button_press(callback: CallbackQuery):
    await callback.answer(text='Ответ неверный. Попробуй еще раз!', show_alert=True)
    await callback.message.edit_reply_markup(yes_keyboard)


# Этот хэндлер будет срабатывать, если во время выбора пола
# будет введено/отправлено что-то некорректное
async def warning_not_first_gift(message: types.Message):
    await message.answer(text='Пожалуйста, пользуйтесь кнопками '
                              'при выборе подарка')


# Этот хэндлер будет срабатывать на нажатие кнопки при
# выборе пола и переводить в состояние отправки фото
async def process_first_gift(callback: CallbackQuery, state: FSMContext):
    # C помощью менеджера контекста сохраняем пол (callback.data нажатой
    # кнопки) в хранилище, по ключу "gender"
    async with state.proxy() as data:
        data['first_gift'] = callback.data
    # Удаляем сообщение с кнопками, потому что следующий этап - загрузка фото
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.edit_text(text='Спасибо! Выбери вторую цифру')

    data = await state.get_data()
    numbers = data.values()
    btns = {}
    for i in range(1, 10):
        btn_name = 'btn_' + str(i)
        if btn_name not in numbers:
            btns[btn_name] = str(i)
    keyboard = create_inline_kb(1, **btns)
    await callback.message.edit_reply_markup(keyboard)

    # Устанавливаем состояние ожидания загрузки фото
    await FSMChooseGifts.second_gift.set()


# Этот хэндлер будет срабатывать, если во время выбора пола
# будет введено/отправлено что-то некорректное
async def warning_not_second_gift(message: types.Message):
    await message.answer(text='Пожалуйста, пользуйтесь кнопками '
                              'при выборе подарка')


async def process_second_gift(callback: CallbackQuery, state: FSMContext):
    # C помощью менеджера контекста сохраняем пол (callback.data нажатой
    # кнопки) в хранилище, по ключу "gender"
    async with state.proxy() as data:
        data['second_gift'] = callback.data
    # Удаляем сообщение с кнопками, потому что следующий этап - загрузка фото
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.edit_text(text='Осталось выбрать последнюю цифру!')

    data = await state.get_data()
    numbers = data.values()
    btns = {}
    for i in range(1, 10):
        btn_name = 'btn_' + str(i)
        if btn_name not in numbers:
            btns[btn_name] = str(i)
    keyboard = create_inline_kb(1, **btns)
    await callback.message.edit_reply_markup(keyboard)

    # Устанавливаем состояние ожидания загрузки фото
    await FSMChooseGifts.third_gift.set()


# Этот хэндлер будет срабатывать, если во время выбора пола
# будет введено/отправлено что-то некорректное
async def warning_not_third_gift(message: types.Message):
    await message.answer(text='Пожалуйста, пользуйтесь кнопками '
                              'при выборе подарка')


async def process_third_gift(callback: CallbackQuery, state: FSMContext):
    # C помощью менеджера контекста сохраняем пол (callback.data нажатой
    # кнопки) в хранилище, по ключу "gender"
    async with state.proxy() as data:
        data['third_gift'] = callback.data
    # Удаляем сообщение с кнопками, потому что следующий этап - загрузка фото
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.edit_text(text='Осталось выбрать последнюю цифру!')

    await give_gifts(callback, state)


async def give_gifts(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.finish()

    numbers = [gift[-1] for gift in data.values()]
    await callback.message.answer(f'Ты выбрал призы {", ".join(numbers)}')

    with open(f'media/gift1/{numbers[0]}.jpg', 'rb') as photo:
        await callback.message.answer_photo(photo)
    with open(f'media/gift2/{numbers[1]}.jpg', 'rb') as photo:
        await callback.message.answer_photo(photo)
    with open(f'media/gift3/{numbers[2]}.jpg', 'rb') as photo:
        await callback.message.answer_photo(photo)

    await asyncio.sleep(3)
    await callback.message.answer('Здесь будет само поздравление')

    with open(f'media/other/second_video.MOV', 'rb') as video:
        await callback.message.answer_video(video)

    await asyncio.sleep(3)
    await callback.message.answer(text='Здесь будет текст: сколько котиков хочешь?', reply_markup=keyboard_for_cats)


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


async def process_number_button_press(callback: CallbackQuery):
    button_pressed = callback.data[0]
    await send_cats(callback, button_pressed)
    await callback.answer(text='На этом все. С Днем рождения!',
                          show_alert=True)
    await callback.message.delete()


# Регистрируем хэндлеры
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
dp.register_message_handler(warning_not_first_gift, state=FSMChooseGifts.first_gift, content_types='any')
dp.register_message_handler(warning_not_second_gift, state=FSMChooseGifts.second_gift, content_types='any')
dp.register_message_handler(warning_not_third_gift, state=FSMChooseGifts.third_gift, content_types='any')
dp.register_callback_query_handler(process_number_button_press, text=['1_button_pressed', '2_button_pressed',
                                                                      '3_button_pressed', '4_button_pressed'])


# Запускаем поллинг
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
