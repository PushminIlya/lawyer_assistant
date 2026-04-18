import os

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from services.branching import get_branch
from services.duty import get_duty_info


# Загружаем переменные из файла .env
load_dotenv()

# Получаем токен бота из переменной окружения
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


# -----------------------------
# Клавиатуры
# -----------------------------

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        ['Определить подсудность'],
        ['Рассчитать госпошлину'],
    ],
    resize_keyboard=True
)

CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        ['Отмена'],
    ],
    resize_keyboard=True
)


# -----------------------------
# Helpers для вывода
# -----------------------------

def format_money(amount: int) -> str:
    return f'{amount:,}'.replace(',', ' ')


def get_procedure_label(branch: str) -> str:
    if branch == 'one_debtor_order':
        return 'приказное производство'

    if branch == 'one_debtor_claim':
        return 'исковое производство'

    return 'не определено'


def get_short_duty_label(duty_type: str) -> str:
    if duty_type == 'court_order':
        return 'Госпошлина (судебный приказ)'

    if duty_type == 'claim':
        return 'Госпошлина (иск)'

    return 'Госпошлина'


def clear_user_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()


# -----------------------------
# Команды
# -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_user_state(context)

    await update.message.reply_text(
        'Привет! Я бот для определения подсудности и расчёта госпошлины.\n'
        'Выбери действие кнопкой ниже.',
        reply_markup=MAIN_KEYBOARD
    )


# -----------------------------
# Логика расчёта госпошлины
# -----------------------------

async def start_duty_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['mode'] = 'waiting_duty_amount'

    await update.message.reply_text(
        'Введите сумму требования в рублях.\n'
        'Например: 95000',
        reply_markup=CANCEL_KEYBOARD
    )


async def handle_duty_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text(
            'Ошибка ввода. Нужно ввести положительное число.\n'
            'Например: 95000'
        )
        return

    amount = int(text)

    if amount <= 0:
        await update.message.reply_text(
            'Ошибка ввода. Сумма должна быть больше нуля.'
        )
        return

    branch = get_branch(debt=amount, debtor_count=1)
    duty_info = get_duty_info(branch, amount)

    procedure_label = get_procedure_label(branch)
    duty_label = get_short_duty_label(duty_info['type'])

    clear_user_state(context)

    await update.message.reply_text(
        'Расчёт готов.\n'
        f'Сумма требования: {format_money(amount)} руб.\n'
        f'Порядок обращения: {procedure_label}.\n'
        f'{duty_label}: {format_money(duty_info["amount"])} руб.',
        reply_markup=MAIN_KEYBOARD
    )


# -----------------------------
# Обработка текста
# -----------------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    mode = context.user_data.get('mode', '')

    if text == 'Отмена':
        clear_user_state(context)

        await update.message.reply_text(
            'Действие отменено.',
            reply_markup=MAIN_KEYBOARD
        )
        return

    if text == 'Определить подсудность':
        clear_user_state(context)

        await update.message.reply_text(
            'Скоро здесь будет пошаговое определение подсудности.',
            reply_markup=MAIN_KEYBOARD
        )
        return

    if text == 'Рассчитать госпошлину':
        await start_duty_flow(update, context)
        return

    if mode == 'waiting_duty_amount':
        await handle_duty_amount(update, context)
        return

    await update.message.reply_text(
        'Я пока понимаю только кнопки меню. Нажми нужную кнопку ниже.',
        reply_markup=MAIN_KEYBOARD
    )


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError('Не найден TELEGRAM_BOT_TOKEN. Проверь файл .env')

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    print('Бот запущен. Нажми Ctrl+C для остановки.')
    application.run_polling()


if __name__ == '__main__':
    main()