from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

keyboard_for_cats: InlineKeyboardMarkup = InlineKeyboardMarkup()

# Создаем объекты инлайн-кнопок
button1: InlineKeyboardButton = InlineKeyboardButton(
    text='1',
    callback_data='1_button_pressed')

button2: InlineKeyboardButton = InlineKeyboardButton(
    text='2',
    callback_data='2_button_pressed')

button3: InlineKeyboardButton = InlineKeyboardButton(
    text='3',
    callback_data='3_button_pressed')

button4: InlineKeyboardButton = InlineKeyboardButton(
    text='4',
    callback_data='4_button_pressed')

# Добавляем кнопки в клавиатуру методом add
keyboard_for_cats.add(button1, button2).add(button3, button4)
