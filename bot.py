import os
from fractions import Fraction

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from services.branching import get_branch
from services.duty import get_duty_info
from services.jurisdiction import get_jurisdiction


load_dotenv()
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


SETTLEMENT_TYPE_CHOICES = [
    'город',
    'село',
    'поселок',
    'рабочий поселок',
    'другое',
]

STREET_TYPE_CHOICES = [
    'улица',
    'переулок',
    'проезд',
    'проспект',
    'бульвар',
    'шоссе',
    'квартал',
    'другое',
]

YES_NO_CHOICES = [
    'да',
    'нет',
]

LIABILITY_TYPE_CHOICES = [
    'долевая',
    'солидарная',
    'не знаю',
]

SHARED_INPUT_MODE_CHOICES = [
    'равные доли',
    'доли дробями',
    'суммы по каждому должнику',
]

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        ['Определить подсудность'],
        ['Рассчитать госпошлину'],
    ],
    resize_keyboard=True,
)

CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[['Отмена']],
    resize_keyboard=True,
)


def build_choice_keyboard(options: list[str]) -> ReplyKeyboardMarkup:
    keyboard = [[option] for option in options]
    keyboard.append(['Отмена'])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def clear_user_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()


def format_money(amount: int) -> str:
    return f'{amount:,}'.replace(',', ' ')


def prettify_text_for_output(text: str) -> str:
    text = str(text).strip()

    if text == '':
        return ''

    words = text.split()
    pretty_words = []

    for word in words:
        if word[0].isalpha():
            pretty_words.append(word[0].upper() + word[1:].lower())
        else:
            pretty_words.append(word)

    return ' '.join(pretty_words)


def format_address(address_data: dict) -> str:
    parts = []

    settlement_type = address_data.get('settlement_type', '')
    settlement_name = prettify_text_for_output(address_data.get('settlement_name', ''))
    street_type = address_data.get('street_type', '')
    street_name = prettify_text_for_output(address_data.get('street_name', ''))
    house = str(address_data.get('house', '')).strip()

    if settlement_type or settlement_name:
        parts.append(f'{settlement_type} {settlement_name}'.strip())

    if street_type or street_name:
        parts.append(f'{street_type} {street_name}'.strip())

    if house:
        parts.append(f'дом {house}')

    return ', '.join(parts)


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


def get_current_address_data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault(
        'address_data',
        {
            'settlement_type': '',
            'settlement_name': '',
            'street_type': '',
            'street_name': '',
            'house': '',
        },
    )


def get_current_jurisdiction_result(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data['jurisdiction_result']


def build_result_text(
    amount: int,
    branch: str,
    address_data: dict,
    jurisdiction: dict,
    title: str = '',
    share_text: str = '',
) -> str:
    duty_info = get_duty_info(branch, amount)
    duty_label = get_short_duty_label(duty_info['type'])
    procedure_label = get_procedure_label(branch)

    lines = []

    if title:
        lines.append(title)

    lines.append(f'Сумма требования: {format_money(amount)} руб.')
    lines.append(f'{duty_label}: {format_money(duty_info["amount"])} руб.')

    if share_text:
        lines.append(f'Размер доли: {share_text}.')

    lines.append('')
    lines.append(f'Адрес должника: {format_address(address_data)}.')
    lines.append(f'Порядок обращения: {procedure_label}.')
    lines.append(f'Уровень суда: {jurisdiction["court_level"]}.')
    lines.append(f'Форма обращения: {jurisdiction["document_type"]}.')

    lines.append('')

    if branch == 'one_debtor_order' and jurisdiction['court_name']:
        lines.append(f'Судебный участок: {jurisdiction["court_name"]}.')

    if branch == 'one_debtor_claim' and jurisdiction['court_name']:
        lines.append(f'Районный суд: {jurisdiction["court_name"]}.')

    if jurisdiction['court_address']:
        lines.append(f'Адрес суда: {jurisdiction["court_address"]}.')

    if jurisdiction['court_phones']:
        lines.append(f'Телефон: {jurisdiction["court_phones"]}.')

    if jurisdiction['court_email']:
        lines.append(f'E-mail: {jurisdiction["court_email"]}.')

    if jurisdiction['court_url']:
        lines.append(f'Сайт: {jurisdiction["court_url"]}.')

    return '\n'.join(lines)


def build_court_key(jurisdiction: dict) -> tuple:
    return (
        jurisdiction.get('court_level', ''),
        jurisdiction.get('court_name', ''),
        jurisdiction.get('court_address', ''),
        jurisdiction.get('court_phones', ''),
        jurisdiction.get('court_email', ''),
        jurisdiction.get('court_url', ''),
        jurisdiction.get('document_type', ''),
    )


def format_court_line(branch: str, jurisdiction: dict) -> str:
    if branch == 'one_debtor_order':
        return f'Судебный участок: {jurisdiction["court_name"]}.'

    return f'Районный суд: {jurisdiction["court_name"]}.'


def build_solidary_variant_text(branch: str, variants: list[dict]) -> str:
    lines = [
        'По адресам солидарных должников получены разные допустимые варианты подсудности.',
        '',
        'Выберите подходящий вариант:',
        'Для выбора напишите номер варианта, например: 1',
    ]

    for index, variant in enumerate(variants, start=1):
        jurisdiction = variant['jurisdiction']
        debtor_numbers = ', '.join([f'№ {number}' for number in variant['debtor_numbers']])

        lines.append('')
        lines.append(f'Вариант {index}.')
        lines.append(f'Должники: {debtor_numbers}.')
        lines.append(format_court_line(branch, jurisdiction))

        if jurisdiction['court_address']:
            lines.append(f'Адрес суда: {jurisdiction["court_address"]}.')

    return '\n'.join(lines)


def build_solidary_result_text(
    total_debt: int,
    branch: str,
    debtors: list[dict],
    jurisdiction: dict,
    note: str = '',
) -> str:
    duty_info = get_duty_info(branch, total_debt)
    duty_label = get_short_duty_label(duty_info['type'])
    procedure_label = get_procedure_label(branch)

    lines = [
        'Солидарные должники.',
        f'Количество должников: {len(debtors)}.',
        f'Общая сумма требования: {format_money(total_debt)} руб.',
        f'{duty_label}: {format_money(duty_info["amount"])} руб.',
        '',
        'Адреса должников:',
    ]

    for debtor in debtors:
        lines.append(
            f'Должник № {debtor["debtor_index"]}: {format_address(debtor["address_data"])}.'
        )

    if note:
        lines.append('')
        lines.append(note)

    lines.append('')
    lines.append(f'Порядок обращения: {procedure_label}.')
    lines.append(f'Уровень суда: {jurisdiction["court_level"]}.')
    lines.append(f'Форма обращения: {jurisdiction["document_type"]}.')

    lines.append('')
    lines.append(format_court_line(branch, jurisdiction))

    if jurisdiction['court_address']:
        lines.append(f'Адрес суда: {jurisdiction["court_address"]}.')

    if jurisdiction['court_phones']:
        lines.append(f'Телефон: {jurisdiction["court_phones"]}.')

    if jurisdiction['court_email']:
        lines.append(f'E-mail: {jurisdiction["court_email"]}.')

    if jurisdiction['court_url']:
        lines.append(f'Сайт: {jurisdiction["court_url"]}.')

    return '\n'.join(lines)


def reset_address_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['address_data'] = {
        'settlement_type': '',
        'settlement_name': '',
        'street_type': '',
        'street_name': '',
        'house': '',
    }


def calculate_equal_shared_amounts(total_debt: int, debtor_count: int) -> tuple[list[int], str]:
    base_amount = total_debt // debtor_count
    remainder = total_debt % debtor_count

    amounts = [base_amount for _ in range(debtor_count)]

    for index in range(remainder):
        amounts[index] += 1

    distribution_comment = ''

    if remainder > 0:
        distribution_comment = (
            'Общая сумма не делится на равные доли без остатка. '
            'Суммы распределены по должникам с округлением до целых рублей.'
        )

    return amounts, distribution_comment


def format_fraction(fraction: Fraction) -> str:
    return f'{fraction.numerator}/{fraction.denominator}'


def parse_share_fraction(text: str) -> Fraction | None:
    normalized = text.strip().replace(' ', '')

    if normalized.count('/') != 1:
        return None

    numerator_text, denominator_text = normalized.split('/')

    if not numerator_text.isdigit() or not denominator_text.isdigit():
        return None

    numerator = int(numerator_text)
    denominator = int(denominator_text)

    if numerator <= 0 or denominator <= 0:
        return None

    share = Fraction(numerator, denominator)

    if share > 1:
        return None

    return share


def calculate_amounts_by_shares(total_debt: int, shares: list[Fraction]) -> tuple[list[int], str]:
    raw_amounts = [Fraction(total_debt) * share for share in shares]
    debtor_amounts = [int(amount) for amount in raw_amounts]

    distributed_sum = sum(debtor_amounts)
    remainder = total_debt - distributed_sum

    if remainder > 0:
        indices = list(range(len(raw_amounts)))
        indices.sort(
            key=lambda index: (raw_amounts[index] - debtor_amounts[index], -index),
            reverse=True,
        )

        for index in indices[:remainder]:
            debtor_amounts[index] += 1

    distribution_comment = ''
    has_fractional_amounts = False

    for amount in raw_amounts:
        if amount != int(amount):
            has_fractional_amounts = True
            break

    if has_fractional_amounts:
        distribution_comment = (
            'Суммы по должникам рассчитаны по долям '
            'с округлением до целых рублей.'
        )

    return debtor_amounts, distribution_comment


async def finish_jurisdiction_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    scenario = context.user_data.get('scenario', 'single')
    amount = context.user_data['amount']
    branch = context.user_data['branch']
    address_data = get_current_address_data(context)
    jurisdiction = get_current_jurisdiction_result(context)

    if scenario == 'single':
        result_text = build_result_text(
            amount=amount,
            branch=branch,
            address_data=address_data,
            jurisdiction=jurisdiction,
            title='Результат готов.',
        )

        clear_user_state(context)

        await update.message.reply_text(
            result_text,
            reply_markup=MAIN_KEYBOARD,
        )
        return

    if scenario == 'shared':
        debtor_index = context.user_data['current_debtor_index']
        debtor_count = context.user_data['debtor_count']
        share_texts = context.user_data['share_texts']
        share_text = share_texts[debtor_index - 1]

        result_text = build_result_text(
            amount=amount,
            branch=branch,
            address_data=address_data,
            jurisdiction=jurisdiction,
            title=f'Результат по должнику № {debtor_index}.',
            share_text=share_text,
        )

        await update.message.reply_text(result_text)

        if debtor_index < debtor_count:
            context.user_data['current_debtor_index'] += 1
            await start_next_shared_debtor(update, context)
            return

        clear_user_state(context)

        await update.message.reply_text(
            'Обработка долевых должников завершена.',
            reply_markup=MAIN_KEYBOARD,
        )
        return

    if scenario == 'solidary':
        debtor_index = context.user_data['current_debtor_index']
        debtor_count = context.user_data['debtor_count']
        solidary_debtors = context.user_data.setdefault('solidary_debtors', [])

        solidary_debtors.append(
            {
                'debtor_index': debtor_index,
                'address_data': dict(address_data),
                'jurisdiction': dict(jurisdiction),
            }
        )

        if debtor_index < debtor_count:
            context.user_data['current_debtor_index'] += 1
            await start_next_solidary_debtor(update, context)
            return

        variants_map = {}

        for debtor in solidary_debtors:
            key = build_court_key(debtor['jurisdiction'])

            if key not in variants_map:
                variants_map[key] = {
                    'jurisdiction': debtor['jurisdiction'],
                    'debtor_numbers': [],
                }

            variants_map[key]['debtor_numbers'].append(debtor['debtor_index'])

        variants = list(variants_map.values())
        solidary_branch = context.user_data['solidary_branch']
        total_debt = context.user_data['total_debt']

        if len(variants) == 1:
            result_text = build_solidary_result_text(
                total_debt=total_debt,
                branch=solidary_branch,
                debtors=solidary_debtors,
                jurisdiction=variants[0]['jurisdiction'],
                note='По всем указанным адресам получен один и тот же суд.',
            )

            clear_user_state(context)

            await update.message.reply_text(
                result_text,
                reply_markup=MAIN_KEYBOARD,
            )
            return

        context.user_data['solidary_variants'] = variants
        context.user_data['mode'] = 'waiting_solidary_variant_choice'

        await update.message.reply_text(
            build_solidary_variant_text(solidary_branch, variants),
            reply_markup=CANCEL_KEYBOARD,
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_user_state(context)

    await update.message.reply_text(
        'Привет! Я бот для определения подсудности и расчёта госпошлины.\n'
        'Выбери действие кнопкой ниже.',
        reply_markup=MAIN_KEYBOARD,
    )


async def start_duty_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_user_state(context)
    context.user_data['mode'] = 'waiting_duty_amount'

    await update.message.reply_text(
        'Введите сумму требования в рублях.\n'
        'Например: 95000',
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_duty_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text(
            'Ошибка ввода. Нужно ввести положительное число.\n'
            'Например: 95000',
        )
        return

    amount = int(text)

    if amount <= 0:
        await update.message.reply_text('Ошибка ввода. Сумма должна быть больше нуля.')
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
        reply_markup=MAIN_KEYBOARD,
    )


async def start_jurisdiction_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_user_state(context)
    context.user_data['mode'] = 'waiting_debtor_count'

    await update.message.reply_text(
        'Введите количество должников.',
        reply_markup=CANCEL_KEYBOARD,
    )


async def ask_liability_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['mode'] = 'waiting_liability_type'

    await update.message.reply_text(
        'Выберите вид ответственности должников:',
        reply_markup=build_choice_keyboard(LIABILITY_TYPE_CHOICES),
    )


async def ask_shared_input_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['mode'] = 'waiting_shared_input_mode'

    await update.message.reply_text(
        'Как заданы доли должников?',
        reply_markup=build_choice_keyboard(SHARED_INPUT_MODE_CHOICES),
    )


async def ask_settlement_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['mode'] = 'waiting_settlement_type'

    await update.message.reply_text(
        'Выберите тип населённого пункта:',
        reply_markup=build_choice_keyboard(SETTLEMENT_TYPE_CHOICES),
    )


async def ask_street_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['mode'] = 'waiting_street_type'

    await update.message.reply_text(
        'Выберите тип улицы / объекта:',
        reply_markup=build_choice_keyboard(STREET_TYPE_CHOICES),
    )


async def ask_completion_street_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['mode'] = 'waiting_completion_street_choice'

    await update.message.reply_text(
        'Нужно ли добавить улицу / иной объект для полного отображения адреса?',
        reply_markup=build_choice_keyboard(YES_NO_CHOICES),
    )


async def ask_completion_house_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['mode'] = 'waiting_completion_house_choice'

    await update.message.reply_text(
        'Нужно ли добавить номер дома для полного отображения адреса?',
        reply_markup=build_choice_keyboard(YES_NO_CHOICES),
    )


async def ask_next_fraction_share(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    share_index = context.user_data['current_share_index']
    debtor_count = context.user_data['debtor_count']

    context.user_data['mode'] = 'waiting_shared_fraction_value'

    await update.message.reply_text(
        f'Введите долю должника № {share_index} из {debtor_count} в формате 1/2, 1/3, 3/4 и т.д.',
        reply_markup=CANCEL_KEYBOARD,
    )


async def ask_next_exact_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    amount_index = context.user_data['current_exact_amount_index']
    debtor_count = context.user_data['debtor_count']

    context.user_data['mode'] = 'waiting_shared_exact_amount'

    await update.message.reply_text(
        f'Введите сумму задолженности для должника № {amount_index} из {debtor_count}.',
        reply_markup=CANCEL_KEYBOARD,
    )


async def start_next_shared_debtor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    debtor_index = context.user_data['current_debtor_index']
    debtor_count = context.user_data['debtor_count']
    debtor_amounts = context.user_data['debtor_amounts']

    current_amount = debtor_amounts[debtor_index - 1]
    current_branch = get_branch(debt=current_amount, debtor_count=1)

    context.user_data['amount'] = current_amount
    context.user_data['branch'] = current_branch
    reset_address_data(context)

    await update.message.reply_text(
        f'--- Должник № {debtor_index} из {debtor_count} ---\n'
        f'Сумма требования: {format_money(current_amount)} руб.',
    )

    await ask_settlement_type(update, context)


async def start_next_solidary_debtor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    debtor_index = context.user_data['current_debtor_index']
    debtor_count = context.user_data['debtor_count']
    total_debt = context.user_data['total_debt']
    solidary_branch = context.user_data['solidary_branch']

    context.user_data['amount'] = total_debt
    context.user_data['branch'] = solidary_branch
    reset_address_data(context)

    await update.message.reply_text(
        f'--- Должник № {debtor_index} из {debtor_count} ---\n'
        f'Общая сумма требования: {format_money(total_debt)} руб.',
    )

    await ask_settlement_type(update, context)


async def handle_debtor_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text('Ошибка ввода. Нужно ввести положительное число.')
        return

    debtor_count = int(text)

    if debtor_count <= 0:
        await update.message.reply_text('Ошибка ввода. Количество должников должно быть больше нуля.')
        return

    context.user_data['debtor_count'] = debtor_count

    if debtor_count == 1:
        context.user_data['scenario'] = 'single'
        context.user_data['mode'] = 'waiting_jurisdiction_amount'

        await update.message.reply_text(
            'Введите сумму требования в рублях.',
            reply_markup=CANCEL_KEYBOARD,
        )
        return

    await ask_liability_type(update, context)


async def handle_liability_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text not in LIABILITY_TYPE_CHOICES:
        await update.message.reply_text('Ошибка ввода. Выберите вид ответственности кнопкой.')
        return

    if text == 'не знаю':
        clear_user_state(context)

        await update.message.reply_text(
            'Не удалось продолжить автоматически.\n'
            'Нужно уточнить, является ли ответственность должников долевой или солидарной.',
            reply_markup=MAIN_KEYBOARD,
        )
        return

    if text == 'солидарная':
        context.user_data['scenario'] = 'solidary'
        context.user_data['mode'] = 'waiting_solidary_total_debt'

        await update.message.reply_text(
            'Введите общую сумму задолженности по всем должникам.',
            reply_markup=CANCEL_KEYBOARD,
        )
        return

    context.user_data['scenario'] = 'shared'
    await ask_shared_input_mode(update, context)


async def handle_shared_input_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text not in SHARED_INPUT_MODE_CHOICES:
        await update.message.reply_text('Ошибка ввода. Выберите вариант кнопкой.')
        return

    context.user_data['shared_input_mode'] = text

    if text == 'равные доли':
        context.user_data['mode'] = 'waiting_shared_total_debt_equal'

        await update.message.reply_text(
            'Введите общую сумму задолженности по всем должникам.',
            reply_markup=CANCEL_KEYBOARD,
        )
        return

    if text == 'доли дробями':
        context.user_data['mode'] = 'waiting_shared_total_debt_fraction'

        await update.message.reply_text(
            'Введите общую сумму задолженности по всем должникам.',
            reply_markup=CANCEL_KEYBOARD,
        )
        return

    context.user_data['mode'] = 'waiting_shared_total_debt_exact'

    await update.message.reply_text(
        'Введите общую сумму задолженности по всем должникам.',
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_shared_total_debt_equal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text('Ошибка ввода. Нужно ввести положительное число.')
        return

    total_debt = int(text)

    if total_debt <= 0:
        await update.message.reply_text('Ошибка ввода. Сумма должна быть больше нуля.')
        return

    debtor_count = context.user_data['debtor_count']
    debtor_amounts, distribution_comment = calculate_equal_shared_amounts(
        total_debt=total_debt,
        debtor_count=debtor_count,
    )

    share_texts = [f'1/{debtor_count}' for _ in range(debtor_count)]

    context.user_data['total_debt'] = total_debt
    context.user_data['debtor_amounts'] = debtor_amounts
    context.user_data['share_texts'] = share_texts
    context.user_data['current_debtor_index'] = 1

    await update.message.reply_text(
        f'Количество должников: {debtor_count}.\n'
        f'Общая сумма требования: {format_money(total_debt)} руб.\n'
        'Доли: равные.',
    )

    if distribution_comment:
        await update.message.reply_text(distribution_comment)

    await start_next_shared_debtor(update, context)


async def handle_shared_total_debt_fraction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text('Ошибка ввода. Нужно ввести положительное число.')
        return

    total_debt = int(text)

    if total_debt <= 0:
        await update.message.reply_text('Ошибка ввода. Сумма должна быть больше нуля.')
        return

    context.user_data['total_debt'] = total_debt
    context.user_data['shares'] = []
    context.user_data['share_texts'] = []
    context.user_data['current_share_index'] = 1

    await ask_next_fraction_share(update, context)


async def handle_shared_total_debt_exact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text('Ошибка ввода. Нужно ввести положительное число.')
        return

    total_debt = int(text)

    if total_debt <= 0:
        await update.message.reply_text('Ошибка ввода. Сумма должна быть больше нуля.')
        return

    context.user_data['total_debt'] = total_debt
    context.user_data['exact_amounts'] = []
    context.user_data['share_texts'] = ['' for _ in range(context.user_data['debtor_count'])]
    context.user_data['current_exact_amount_index'] = 1

    await ask_next_exact_amount(update, context)


async def handle_solidary_total_debt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text('Ошибка ввода. Нужно ввести положительное число.')
        return

    total_debt = int(text)

    if total_debt <= 0:
        await update.message.reply_text('Ошибка ввода. Сумма должна быть больше нуля.')
        return

    context.user_data['total_debt'] = total_debt
    context.user_data['solidary_branch'] = get_branch(debt=total_debt, debtor_count=1)
    context.user_data['solidary_debtors'] = []
    context.user_data['current_debtor_index'] = 1

    await update.message.reply_text(
        f'Количество должников: {context.user_data["debtor_count"]}.\n'
        f'Общая сумма требования: {format_money(total_debt)} руб.',
    )

    await start_next_solidary_debtor(update, context)


async def handle_shared_fraction_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    share = parse_share_fraction(text)

    if share is None:
        await update.message.reply_text(
            'Ошибка ввода. Доля должна быть в формате числитель/знаменатель, например 1/2.',
        )
        return

    shares = context.user_data['shares']
    share_texts = context.user_data['share_texts']
    debtor_count = context.user_data['debtor_count']
    total_debt = context.user_data['total_debt']
    current_share_index = context.user_data['current_share_index']

    shares.append(share)
    share_texts.append(format_fraction(share))

    if current_share_index < debtor_count:
        context.user_data['current_share_index'] += 1
        await ask_next_fraction_share(update, context)
        return

    total_share = sum(shares, start=Fraction(0, 1))

    if total_share != 1:
        context.user_data['shares'] = []
        context.user_data['share_texts'] = []
        context.user_data['current_share_index'] = 1

        await update.message.reply_text(
            'Ошибка ввода. Сумма долей должна быть равна 1.\n'
            'Давайте введём доли заново.',
        )
        await ask_next_fraction_share(update, context)
        return

    debtor_amounts, distribution_comment = calculate_amounts_by_shares(
        total_debt=total_debt,
        shares=shares,
    )

    context.user_data['debtor_amounts'] = debtor_amounts
    context.user_data['current_debtor_index'] = 1

    await update.message.reply_text(
        f'Количество должников: {debtor_count}.\n'
        f'Общая сумма требования: {format_money(total_debt)} руб.\n'
        'Доли: заданы дробями.',
    )

    if distribution_comment:
        await update.message.reply_text(distribution_comment)

    await start_next_shared_debtor(update, context)


async def handle_shared_exact_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text('Ошибка ввода. Нужно ввести положительное число.')
        return

    amount = int(text)

    if amount <= 0:
        await update.message.reply_text('Ошибка ввода. Сумма должна быть больше нуля.')
        return

    exact_amounts = context.user_data['exact_amounts']
    total_debt = context.user_data['total_debt']
    current_exact_amount_index = context.user_data['current_exact_amount_index']
    debtor_count = context.user_data['debtor_count']

    exact_amounts.append(amount)

    if current_exact_amount_index < debtor_count:
        context.user_data['current_exact_amount_index'] += 1
        await ask_next_exact_amount(update, context)
        return

    if sum(exact_amounts) != total_debt:
        context.user_data['exact_amounts'] = []
        context.user_data['current_exact_amount_index'] = 1

        await update.message.reply_text(
            'Ошибка ввода. Сумма по должникам не равна общей сумме задолженности.\n'
            'Давайте введём суммы заново.',
        )
        await ask_next_exact_amount(update, context)
        return

    context.user_data['debtor_amounts'] = exact_amounts.copy()
    context.user_data['current_debtor_index'] = 1

    await update.message.reply_text(
        f'Количество должников: {debtor_count}.\n'
        f'Общая сумма требования: {format_money(total_debt)} руб.\n'
        'Суммы заданы отдельно по каждому должнику.',
    )

    await start_next_shared_debtor(update, context)


async def handle_solidary_variant_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text('Ошибка ввода. Нужно ввести номер варианта.')
        return

    variant_number = int(text)
    variants = context.user_data['solidary_variants']

    if variant_number < 1 or variant_number > len(variants):
        await update.message.reply_text('Ошибка ввода. Выберите существующий номер варианта.')
        return

    chosen_variant = variants[variant_number - 1]
    result_text = build_solidary_result_text(
        total_debt=context.user_data['total_debt'],
        branch=context.user_data['solidary_branch'],
        debtors=context.user_data['solidary_debtors'],
        jurisdiction=chosen_variant['jurisdiction'],
        note=f'Выбран вариант подсудности по адресам должников: № {variant_number}.',
    )

    clear_user_state(context)

    await update.message.reply_text(
        result_text,
        reply_markup=MAIN_KEYBOARD,
    )


async def handle_jurisdiction_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text('Ошибка ввода. Нужно ввести положительное число.')
        return

    amount = int(text)

    if amount <= 0:
        await update.message.reply_text('Ошибка ввода. Сумма должна быть больше нуля.')
        return

    branch = get_branch(debt=amount, debtor_count=1)

    context.user_data['amount'] = amount
    context.user_data['branch'] = branch
    reset_address_data(context)

    await ask_settlement_type(update, context)


async def handle_settlement_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text not in SETTLEMENT_TYPE_CHOICES:
        await update.message.reply_text('Ошибка ввода. Выберите тип населённого пункта кнопкой.')
        return

    address_data = get_current_address_data(context)

    if text == 'другое':
        context.user_data['mode'] = 'waiting_settlement_type_manual'
        await update.message.reply_text(
            'Введите тип населённого пункта вручную:',
            reply_markup=CANCEL_KEYBOARD,
        )
        return

    address_data['settlement_type'] = text
    context.user_data['mode'] = 'waiting_settlement_name'

    await update.message.reply_text(
        'Введите название населённого пункта:',
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_settlement_type_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text == '':
        await update.message.reply_text('Ошибка ввода. Поле не должно быть пустым.')
        return

    address_data = get_current_address_data(context)
    address_data['settlement_type'] = text
    context.user_data['mode'] = 'waiting_settlement_name'

    await update.message.reply_text(
        'Введите название населённого пункта:',
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_settlement_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text == '':
        await update.message.reply_text('Ошибка ввода. Поле не должно быть пустым.')
        return

    address_data = get_current_address_data(context)
    branch = context.user_data['branch']

    address_data['settlement_name'] = text
    address_data['street_type'] = ''
    address_data['street_name'] = ''
    address_data['house'] = ''

    jurisdiction = get_jurisdiction(branch, address_data)

    if jurisdiction['status'] == 'resolved':
        context.user_data['jurisdiction_result'] = jurisdiction
        await ask_completion_street_choice(update, context)
        return

    if jurisdiction['status'] == 'invalid_settlement':
        await update.message.reply_text('Населённый пункт не найден. Попробуйте снова.')
        await ask_settlement_type(update, context)
        return

    await update.message.reply_text(jurisdiction['comment'])
    await ask_street_type(update, context)


async def handle_street_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text not in STREET_TYPE_CHOICES:
        await update.message.reply_text('Ошибка ввода. Выберите тип улицы / объекта кнопкой.')
        return

    address_data = get_current_address_data(context)

    if text == 'другое':
        context.user_data['mode'] = 'waiting_street_type_manual'
        await update.message.reply_text(
            'Введите тип улицы / объекта вручную:',
            reply_markup=CANCEL_KEYBOARD,
        )
        return

    address_data['street_type'] = text
    context.user_data['mode'] = 'waiting_street_name'

    await update.message.reply_text(
        'Введите название улицы / объекта:',
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_street_type_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text == '':
        await update.message.reply_text('Ошибка ввода. Поле не должно быть пустым.')
        return

    address_data = get_current_address_data(context)
    address_data['street_type'] = text
    context.user_data['mode'] = 'waiting_street_name'

    await update.message.reply_text(
        'Введите название улицы / объекта:',
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_street_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text == '':
        await update.message.reply_text('Ошибка ввода. Поле не должно быть пустым.')
        return

    address_data = get_current_address_data(context)
    branch = context.user_data['branch']

    address_data['street_name'] = text
    address_data['house'] = ''

    jurisdiction = get_jurisdiction(branch, address_data)

    if jurisdiction['status'] == 'resolved':
        context.user_data['jurisdiction_result'] = jurisdiction
        await ask_completion_house_choice(update, context)
        return

    if jurisdiction['status'] == 'invalid_street':
        await update.message.reply_text('Улица или иной объект не найдены. Попробуйте снова.')
        await ask_street_type(update, context)
        return

    context.user_data['mode'] = 'waiting_house'

    await update.message.reply_text(
        'Введите номер дома:',
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_house(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text == '':
        await update.message.reply_text('Ошибка ввода. Поле не должно быть пустым.')
        return

    address_data = get_current_address_data(context)
    branch = context.user_data['branch']

    address_data['house'] = text

    jurisdiction = get_jurisdiction(branch, address_data)

    if jurisdiction['status'] == 'resolved':
        context.user_data['jurisdiction_result'] = jurisdiction
        await finish_jurisdiction_flow(update, context)
        return

    await update.message.reply_text(
        'Подсудность по введённым данным определить не удалось.\n'
        'Нажми "Определить подсудность" и попробуй ещё раз.',
        reply_markup=MAIN_KEYBOARD,
    )
    clear_user_state(context)


async def handle_completion_street_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text not in YES_NO_CHOICES:
        await update.message.reply_text('Ошибка ввода. Выберите "да" или "нет" кнопкой.')
        return

    if text == 'нет':
        await ask_completion_house_choice(update, context)
        return

    context.user_data['mode'] = 'waiting_completion_street_type'

    await update.message.reply_text(
        'Выберите тип улицы / объекта:',
        reply_markup=build_choice_keyboard(STREET_TYPE_CHOICES),
    )


async def handle_completion_street_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text not in STREET_TYPE_CHOICES:
        await update.message.reply_text('Ошибка ввода. Выберите тип улицы / объекта кнопкой.')
        return

    address_data = get_current_address_data(context)

    if text == 'другое':
        context.user_data['mode'] = 'waiting_completion_street_type_manual'
        await update.message.reply_text(
            'Введите тип улицы / объекта вручную:',
            reply_markup=CANCEL_KEYBOARD,
        )
        return

    address_data['street_type'] = text
    context.user_data['mode'] = 'waiting_completion_street_name'

    await update.message.reply_text(
        'Введите название улицы / объекта:',
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_completion_street_type_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text == '':
        await update.message.reply_text('Ошибка ввода. Поле не должно быть пустым.')
        return

    address_data = get_current_address_data(context)
    address_data['street_type'] = text
    context.user_data['mode'] = 'waiting_completion_street_name'

    await update.message.reply_text(
        'Введите название улицы / объекта:',
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_completion_street_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text == '':
        await update.message.reply_text('Ошибка ввода. Поле не должно быть пустым.')
        return

    address_data = get_current_address_data(context)
    address_data['street_name'] = text

    await ask_completion_house_choice(update, context)


async def handle_completion_house_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text not in YES_NO_CHOICES:
        await update.message.reply_text('Ошибка ввода. Выберите "да" или "нет" кнопкой.')
        return

    if text == 'нет':
        await finish_jurisdiction_flow(update, context)
        return

    context.user_data['mode'] = 'waiting_completion_house'

    await update.message.reply_text(
        'Введите номер дома:',
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_completion_house(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if text == '':
        await update.message.reply_text('Ошибка ввода. Поле не должно быть пустым.')
        return

    address_data = get_current_address_data(context)
    address_data['house'] = text

    await finish_jurisdiction_flow(update, context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    mode = context.user_data.get('mode', '')

    if text == 'Отмена':
        clear_user_state(context)

        await update.message.reply_text(
            'Действие отменено.',
            reply_markup=MAIN_KEYBOARD,
        )
        return

    if text == 'Рассчитать госпошлину':
        await start_duty_flow(update, context)
        return

    if text == 'Определить подсудность':
        await start_jurisdiction_flow(update, context)
        return

    if mode == 'waiting_duty_amount':
        await handle_duty_amount(update, context)
        return

    if mode == 'waiting_debtor_count':
        await handle_debtor_count(update, context)
        return

    if mode == 'waiting_liability_type':
        await handle_liability_type(update, context)
        return

    if mode == 'waiting_shared_input_mode':
        await handle_shared_input_mode(update, context)
        return

    if mode == 'waiting_shared_total_debt_equal':
        await handle_shared_total_debt_equal(update, context)
        return

    if mode == 'waiting_shared_total_debt_fraction':
        await handle_shared_total_debt_fraction(update, context)
        return

    if mode == 'waiting_shared_total_debt_exact':
        await handle_shared_total_debt_exact(update, context)
        return

    if mode == 'waiting_solidary_total_debt':
        await handle_solidary_total_debt(update, context)
        return

    if mode == 'waiting_shared_fraction_value':
        await handle_shared_fraction_value(update, context)
        return

    if mode == 'waiting_shared_exact_amount':
        await handle_shared_exact_amount(update, context)
        return

    if mode == 'waiting_solidary_variant_choice':
        await handle_solidary_variant_choice(update, context)
        return

    if mode == 'waiting_jurisdiction_amount':
        await handle_jurisdiction_amount(update, context)
        return

    if mode == 'waiting_settlement_type':
        await handle_settlement_type(update, context)
        return

    if mode == 'waiting_settlement_type_manual':
        await handle_settlement_type_manual(update, context)
        return

    if mode == 'waiting_settlement_name':
        await handle_settlement_name(update, context)
        return

    if mode == 'waiting_street_type':
        await handle_street_type(update, context)
        return

    if mode == 'waiting_street_type_manual':
        await handle_street_type_manual(update, context)
        return

    if mode == 'waiting_street_name':
        await handle_street_name(update, context)
        return

    if mode == 'waiting_house':
        await handle_house(update, context)
        return

    if mode == 'waiting_completion_street_choice':
        await handle_completion_street_choice(update, context)
        return

    if mode == 'waiting_completion_street_type':
        await handle_completion_street_type(update, context)
        return

    if mode == 'waiting_completion_street_type_manual':
        await handle_completion_street_type_manual(update, context)
        return

    if mode == 'waiting_completion_street_name':
        await handle_completion_street_name(update, context)
        return

    if mode == 'waiting_completion_house_choice':
        await handle_completion_house_choice(update, context)
        return

    if mode == 'waiting_completion_house':
        await handle_completion_house(update, context)
        return

    await update.message.reply_text(
        'Я пока понимаю только кнопки меню. Нажми нужную кнопку ниже.',
        reply_markup=MAIN_KEYBOARD,
    )


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError('Не найден TELEGRAM_BOT_TOKEN. Проверь файл .env')

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print('Бот запущен. Нажми Ctrl+C для остановки.')
    application.run_polling()


if __name__ == '__main__':
    main()




