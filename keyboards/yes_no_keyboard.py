# Создаем объект инлайн-клавиатуры
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

question_keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup()

# Создаем объекты инлайн-кнопок
yes_button: InlineKeyboardButton = InlineKeyboardButton(
    text='Да!',
    callback_data='yes_button_pressed')

no_button: InlineKeyboardButton = InlineKeyboardButton(
    text='Нет.',
    callback_data='no_button_pressed')

# Добавляем кнопки в клавиатуру методом add
question_keyboard.add(yes_button).add(no_button)

yes_keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup()

yes_keyboard.add(yes_button)
