from consts import API_CATS_URL
from db_client import DBClient

import os
import asyncio

import requests
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
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

# Создаем "базу данных" пользователей
user_dict: dict[int, dict[str, str | int]] = {}


# Cоздаем класс, наследуемый от StatesGroup, для группы состояний нашей FSM
class FSMFillForm(StatesGroup):
    # Создаем экземпляры класса State, последовательно
    # перечисляя возможные состояния, в которых будет находиться
    # бот в разные моменты взаимодействия с пользователем
    fill_username = State()        # Состояние ожидания ввода логина
    fill_password = State()        # Состояние ожидания ввода пароля


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
                              'Если хочешь прервать заполнение анкеты - отправь команду /cancel'
                         )


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
                                  'Если хочешь прервать заполнение анкеты - отправь команду /cancel'
                             )


# Этот хэндлер будет срабатывать, если во время ввода пароля
# будет введено что-то некорректное
async def warning_not_password(message: types.Message):
    await message.answer(text='То, что ты отправил не похоже на пароль\n'
                              'Пожалуйста, введи корректный пароль\n\n'
                              'Если хочешь прервать заполнение анкеты - отправь команду /cancel'
                         )


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

    await message.answer('some text')


# Регистрируем хэндлеры
dp.register_message_handler(process_cancel_command, commands='cancel', state='*')
dp.register_message_handler(process_username_sent, content_types='text', state=FSMFillForm.fill_username)
dp.register_message_handler(warning_not_username, content_types='any', state=FSMFillForm.fill_username)
dp.register_message_handler(process_password_sent, content_types='text', state=FSMFillForm.fill_password)
dp.register_message_handler(warning_not_password, content_types='any', state=FSMFillForm.fill_password)


# Запускаем поллинг
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
