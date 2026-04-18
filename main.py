from fractions import Fraction

from services.branching import get_branch
from services.duty import get_duty_info
from services.jurisdiction import get_jurisdiction


# -----------------------------
# Константы для меню
# -----------------------------

SETTLEMENT_TYPE_CHOICES = {
    '1': 'город',
    '2': 'село',
    '3': 'поселок',
    '4': 'рабочий поселок',
    '5': 'другое'
}

STREET_TYPE_CHOICES = {
    '1': 'улица',
    '2': 'переулок',
    '3': 'проезд',
    '4': 'проспект',
    '5': 'бульвар',
    '6': 'шоссе',
    '7': 'квартал',
    '8': 'другое'
}

RETRY_ADDRESS_CHOICES = {
    '1': 'повторить ввод номера дома',
    '2': 'повторить ввод улицы / объекта',
    '3': 'повторить ввод населённого пункта'
}

LIABILITY_TYPE_CHOICES = {
    '1': 'долевая',
    '2': 'солидарная',
    '3': 'не знаю'
}

SHARED_DEBT_INPUT_CHOICES = {
    '1': 'доли равные',
    '2': 'доли в виде дробей',
    '3': 'суммы по каждому должнику',
    '4': 'не знаю'
}

YES_NO_CHOICES = {
    '1': 'да',
    '2': 'нет'
}


# -----------------------------
# Универсальные функции ввода
# -----------------------------

# Показывает меню и возвращает выбранное значение.
def input_menu_choice(prompt: str, choices: dict) -> str:
    while True:
        print(prompt)

        for key, value in choices.items():
            print(f'{key} - {value}')

        choice = input('Ваш выбор: ').strip()

        if choice in choices:
            return choices[choice]

        print('Ошибка ввода. Выберите значение из предложенных.')


# Запрашивает положительное целое число.
def input_positive_number(prompt: str) -> int:
    while True:
        value = input(prompt).strip()

        if not value.isdigit():
            print('Ошибка ввода. Нужно ввести положительное число.')
            continue

        number = int(value)

        if number <= 0:
            print('Ошибка ввода. Нужно ввести число больше нуля.')
            continue

        return number


# Запрашивает непустую строку.
def input_nonempty_text(prompt: str) -> str:
    while True:
        value = input(prompt).strip()

        if value == '':
            print('Ошибка ввода. Поле не должно быть пустым.')
            continue

        return value


# Используется там, где нужно выбрать номер в диапазоне.
def input_number_in_range(prompt: str, min_value: int, max_value: int) -> int:
    while True:
        value = input(prompt).strip()

        if not value.isdigit():
            print('Ошибка ввода. Нужно ввести число.')
            continue

        number = int(value)

        if number < min_value or number > max_value:
            print(f'Ошибка ввода. Введите число от {min_value} до {max_value}.')
            continue

        return number


# Выбор вида ресурса.
def input_resource_type() -> str:
    while True:
        resource_choice = input(
            'Введите вид ресурса (электроэнергия - 1, теплоэнергия - 2): '
        ).strip()

        if resource_choice not in ('1', '2'):
            print('Ошибка ввода. Выберите вид ресурса из предложенных.')
            continue

        if resource_choice == '1':
            return 'электроэнергия'

        return 'теплоэнергия'


# Выбор типа ответственности при нескольких должниках.
def input_liability_type() -> str:
    choice = input_menu_choice(
        'Выберите вид ответственности должников:',
        LIABILITY_TYPE_CHOICES
    )

    if choice == 'долевая':
        return 'shared'

    if choice == 'солидарная':
        return 'solidary'

    return 'unknown'


# -----------------------------
# Форматирование вывода
# -----------------------------

# Делает строку визуально аккуратнее для вывода пользователю.
# На поиск подсудности не влияет.
def prettify_text_for_output(text: str) -> str:
    text = str(text).strip()

    if text == '':
        return ''

    words = text.split()
    pretty_words = []

    for word in words:
        if word[0].isalpha():
            pretty_words.append(word[0].upper() + word[1:])
        else:
            pretty_words.append(word)

    return ' '.join(pretty_words)


# Форматирует сумму с пробелами между разрядами.
# Например: 255000 -> "255 000"
def format_money(amount: int) -> str:
    return f'{amount:,}'.replace(',', ' ')


# Приводит дробь к строке вида 1/2.
def format_fraction(fraction: Fraction) -> str:
    return f'{fraction.numerator}/{fraction.denominator}'


# Собирает красивую строку адреса для итогового вывода.
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


# Преобразует список номеров должников в строку:
# [1, 2, 4] -> "№ 1, № 2, № 4"
def format_debtor_indexes(indexes: list[int]) -> str:
    return ', '.join(f'№ {index}' for index in indexes)


# -----------------------------
# Небольшие логические helpers
# -----------------------------

# Короткое понятное название госпошлины.
def get_short_duty_label(duty_type: str) -> str:
    if duty_type == 'court_order':
        return 'Госпошлина (судебный приказ)'

    if duty_type == 'claim':
        return 'Госпошлина (иск)'

    return 'Госпошлина'


# Короткое название порядка обращения.
def get_procedure_label(branch: str) -> str:
    if branch == 'one_debtor_order':
        return 'приказное производство'

    if branch == 'one_debtor_claim':
        return 'исковое производство'

    return ''


# Для отдельной суммы определяет, это приказ или иск.
def get_single_branch_for_amount(amount: int) -> str:
    if amount <= 500000:
        return 'one_debtor_order'

    return 'one_debtor_claim'


# Формирует ключ суда для группировки одинаковых вариантов.
def build_court_key(branch: str, jurisdiction: dict) -> tuple:
    return (
        branch,
        jurisdiction.get('court_name', ''),
        jurisdiction.get('court_address', ''),
        jurisdiction.get('court_phones', ''),
        jurisdiction.get('court_email', ''),
        jurisdiction.get('court_url', '')
    )


# -----------------------------
# Работа с долями
# -----------------------------

# Разбирает долю в формате "1/2".
# Если формат неверный, возвращает None.
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


# Считает суммы по долям и распределяет остаток в целых рублях.
def calculate_amounts_by_shares(
    total_debt: int,
    shares: list[Fraction]
) -> tuple[list[int], str]:
    raw_amounts = [Fraction(total_debt) * share for share in shares]

    # Сначала берём целую часть каждому.
    debtor_amounts = [int(amount) for amount in raw_amounts]

    distributed_sum = sum(debtor_amounts)
    remainder = total_debt - distributed_sum

    # Если остались рубли после округления вниз,
    # распределяем их по наибольшим дробным остаткам.
    if remainder > 0:
        indices = list(range(len(raw_amounts)))

        indices.sort(
            key=lambda index: (raw_amounts[index] - debtor_amounts[index], -index),
            reverse=True
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


# Ввод долей в формате дробей.
def input_fraction_shares(debtor_count: int) -> tuple[list[Fraction], list[str]]:
    while True:
        shares = []
        share_texts = []

        print('Введите долю каждого должника в формате 1/2, 1/3, 3/4 и т.д.')

        for index in range(1, debtor_count + 1):
            while True:
                share_text = input_nonempty_text(
                    f'Должник № {index}, доля: '
                )

                share = parse_share_fraction(share_text)

                if share is None:
                    print('Ошибка ввода. Доля должна быть в формате числитель/знаменатель, например 1/2.')
                    continue

                shares.append(share)
                share_texts.append(format_fraction(share))
                break

        total_share = sum(shares, start=Fraction(0, 1))

        if total_share != 1:
            print('Ошибка ввода. Сумма долей должна быть равна 1.')
            print('Повторите ввод долей ещё раз.')
            continue

        return shares, share_texts


# Ввод точных сумм по каждому должнику.
def input_exact_shared_amounts(total_debt: int, debtor_count: int) -> list[int]:
    while True:
        debtor_amounts = []

        print('Введите сумму задолженности по каждому должнику:')

        for index in range(1, debtor_count + 1):
            amount = input_positive_number(
                f'Должник № {index}, сумма задолженности: '
            )
            debtor_amounts.append(amount)

        if sum(debtor_amounts) != total_debt:
            print('Ошибка ввода. Сумма по должникам не равна общей сумме задолженности.')
            print('Повторите ввод сумм ещё раз.')
            continue

        return debtor_amounts


# Собирает все данные по долевой ответственности.
def input_shared_debt_data(debtor_count: int) -> dict:
    total_debt = input_positive_number(
        'Введите общую сумму задолженности по всем должникам: '
    )

    input_mode = input_menu_choice(
        'Как заданы доли должников?',
        SHARED_DEBT_INPUT_CHOICES
    )

    if input_mode == 'не знаю':
        return {
            'status': 'unknown',
            'total_debt': total_debt,
            'debtor_amounts': [],
            'share_texts': [],
            'distribution_comment': ''
        }

    if input_mode == 'доли равные':
        shares = [Fraction(1, debtor_count) for _ in range(debtor_count)]
        share_texts = [format_fraction(share) for share in shares]
        debtor_amounts, distribution_comment = calculate_amounts_by_shares(
            total_debt,
            shares
        )

        if total_debt % debtor_count != 0:
            distribution_comment = (
                'Общая сумма не делится на равные доли без остатка. '
                'Суммы распределены по должникам с округлением до целых рублей.'
            )

        return {
            'status': 'ok',
            'total_debt': total_debt,
            'debtor_amounts': debtor_amounts,
            'share_texts': share_texts,
            'distribution_comment': distribution_comment
        }

    if input_mode == 'доли в виде дробей':
        shares, share_texts = input_fraction_shares(debtor_count)
        debtor_amounts, distribution_comment = calculate_amounts_by_shares(
            total_debt,
            shares
        )

        return {
            'status': 'ok',
            'total_debt': total_debt,
            'debtor_amounts': debtor_amounts,
            'share_texts': share_texts,
            'distribution_comment': distribution_comment
        }

    debtor_amounts = input_exact_shared_amounts(total_debt, debtor_count)

    return {
        'status': 'ok',
        'total_debt': total_debt,
        'debtor_amounts': debtor_amounts,
        'share_texts': ['' for _ in range(debtor_count)],
        'distribution_comment': ''
    }


# -----------------------------
# Вывод информации о суде
# -----------------------------

# Печатает порядок обращения.
def print_procedure(branch: str) -> None:
    procedure_label = get_procedure_label(branch)

    if procedure_label:
        print(f'Порядок обращения: {procedure_label}.')


# Печатает основную информацию о суде.
def print_court_info(branch: str, jurisdiction: dict) -> None:
    print(f'Уровень суда: {jurisdiction["court_level"]}.')
    print(f'Форма обращения: {jurisdiction["document_type"]}.')

    if branch == 'one_debtor_order' and jurisdiction['court_name']:
        print(f'Судебный участок: {jurisdiction["court_name"]}.')

    if branch == 'one_debtor_claim' and jurisdiction['court_name']:
        print(f'Районный суд: {jurisdiction["court_name"]}.')


# Печатает контактные данные суда.
def print_court_contacts(jurisdiction: dict) -> None:
    if jurisdiction['court_address']:
        print(f'Адрес суда: {jurisdiction["court_address"]}.')

    if jurisdiction['court_phones']:
        print(f'Телефон: {jurisdiction["court_phones"]}.')

    if jurisdiction['court_email']:
        print(f'E-mail: {jurisdiction["court_email"]}.')

    if jurisdiction['court_url']:
        print(f'Сайт: {jurisdiction["court_url"]}.')


# Печатает результат по одному должнику.
def print_single_result(
    type_of_energy_resource: str,
    debt: int,
    branch: str,
    address_data: dict,
    jurisdiction: dict,
    title: str = '',
    share_text: str = ''
) -> None:
    if title:
        print()
        print(title)

    duty_info = get_duty_info(branch, debt)
    duty_label = get_short_duty_label(duty_info['type'])

    print(f'Ресурс: {type_of_energy_resource}.')
    print(f'Сумма требования: {format_money(debt)} руб.')
    print(f'{duty_label}: {format_money(duty_info["amount"])} руб.')

    if share_text:
        print(f'Размер доли: {share_text}.')

    if address_data:
        print(f'Адрес должника: {format_address(address_data)}.')

    print_procedure(branch)
    print_court_info(branch, jurisdiction)
    print_court_contacts(jurisdiction)


# -----------------------------
# Ввод адреса
# -----------------------------

# Дозаполняет адрес только для красивого итогового вывода.
# На определение подсудности не влияет.
def complete_address_for_output(address_data: dict) -> dict:
    if not address_data.get('street_name'):
        has_street = input_menu_choice(
            'Нужно ли добавить улицу / иной объект для полного отображения адреса?',
            YES_NO_CHOICES
        )

        if has_street == 'да':
            street_type = input_menu_choice(
                'Выберите тип улицы / объекта:',
                STREET_TYPE_CHOICES
            )

            if street_type == 'другое':
                street_type = input_nonempty_text(
                    'Введите тип улицы / объекта вручную: '
                )

            street_name = input_nonempty_text(
                'Введите название улицы / объекта: '
            )

            address_data['street_type'] = street_type
            address_data['street_name'] = street_name

    if not address_data.get('house'):
        has_house = input_menu_choice(
            'Нужно ли добавить номер дома для полного отображения адреса?',
            YES_NO_CHOICES
        )

        if has_house == 'да':
            house = input_nonempty_text('Введите номер дома: ')
            address_data['house'] = house

    return address_data


# Пошаговый ввод адреса.
def input_address(branch: str) -> tuple[dict, dict]:
    address_data = {
        'settlement_type': '',
        'settlement_name': '',
        'street_type': '',
        'street_name': '',
        'house': ''
    }

    while True:
        # --- Шаг 1. Населённый пункт ---
        settlement_type = input_menu_choice(
            'Выберите тип населённого пункта:',
            SETTLEMENT_TYPE_CHOICES
        )

        if settlement_type == 'другое':
            settlement_type = input_nonempty_text(
                'Введите тип населённого пункта вручную: '
            )

        settlement_name = input_nonempty_text(
            'Введите название населённого пункта: '
        )

        address_data['settlement_type'] = settlement_type
        address_data['settlement_name'] = settlement_name

        address_data['street_type'] = ''
        address_data['street_name'] = ''
        address_data['house'] = ''

        jurisdiction = get_jurisdiction(branch, address_data)

        if jurisdiction['status'] == 'resolved':
            address_data = complete_address_for_output(address_data)
            return address_data, jurisdiction

        if jurisdiction['status'] == 'invalid_settlement':
            print('Ошибка ввода. Населённый пункт не найден. Попробуйте ещё раз.')
            continue

        print(jurisdiction['comment'])

        restart_settlement = False

        while True:
            # --- Шаг 2. Улица / объект ---
            street_type = input_menu_choice(
                'Выберите тип улицы / объекта:',
                STREET_TYPE_CHOICES
            )

            if street_type == 'другое':
                street_type = input_nonempty_text(
                    'Введите тип улицы / объекта вручную: '
                )

            street_name = input_nonempty_text(
                'Введите название улицы / объекта: '
            )

            address_data['street_type'] = street_type
            address_data['street_name'] = street_name
            address_data['house'] = ''

            jurisdiction = get_jurisdiction(branch, address_data)

            if jurisdiction['status'] == 'resolved':
                address_data = complete_address_for_output(address_data)
                return address_data, jurisdiction

            if jurisdiction['status'] == 'invalid_street':
                print('Ошибка ввода. Улица или иной объект не найдены. Попробуйте ещё раз.')
                continue

            print(jurisdiction['comment'])

            while True:
                # --- Шаг 3. Дом ---
                house = input_nonempty_text('Введите номер дома: ')
                address_data['house'] = house

                jurisdiction = get_jurisdiction(branch, address_data)

                if jurisdiction['status'] == 'resolved':
                    address_data = complete_address_for_output(address_data)
                    return address_data, jurisdiction

                print('Подсудность по введённым данным определить не удалось.')

                retry_action = input_menu_choice(
                    'Что хотите исправить?',
                    RETRY_ADDRESS_CHOICES
                )

                if retry_action == 'повторить ввод номера дома':
                    continue

                if retry_action == 'повторить ввод улицы / объекта':
                    address_data['house'] = ''
                    break

                address_data['street_type'] = ''
                address_data['street_name'] = ''
                address_data['house'] = ''
                restart_settlement = True
                break

            if restart_settlement:
                break

        if restart_settlement:
            continue


# -----------------------------
# Солидарные должники
# -----------------------------

# Группирует одинаковые варианты суда.
def group_solidary_options(branch: str, debtors: list[dict]) -> list[dict]:
    grouped = {}

    for debtor in debtors:
        jurisdiction = debtor['jurisdiction']
        key = build_court_key(branch, jurisdiction)

        if key not in grouped:
            grouped[key] = {
                'jurisdiction': jurisdiction,
                'debtors': [],
                'addresses': []
            }

        grouped[key]['debtors'].append(debtor['index'])
        grouped[key]['addresses'].append(format_address(debtor['address_data']))

    options = list(grouped.values())
    options.sort(key=lambda option: option['debtors'][0])

    return options


# Печатает список адресов всех солидарных должников.
def print_all_solidary_debtors(debtors: list[dict]) -> None:
    print('Адреса должников:')

    for debtor in debtors:
        print(f'Должник № {debtor["index"]}: {format_address(debtor["address_data"])}.')


# Печатает итог по солидарным должникам.
def print_solidary_result(
    type_of_energy_resource: str,
    total_debt: int,
    branch: str,
    debtors: list[dict],
    selected_option: dict,
    has_multiple_options: bool
) -> None:
    jurisdiction = selected_option['jurisdiction']
    debtor_indexes = selected_option['debtors']
    duty_info = get_duty_info(branch, total_debt)
    duty_label = get_short_duty_label(duty_info['type'])

    print()
    print('Солидарные должники.')
    print(f'Количество должников: {len(debtors)}.')
    print(f'Общая сумма требования: {format_money(total_debt)} руб.')
    print(f'{duty_label}: {format_money(duty_info["amount"])} руб.')

    print_all_solidary_debtors(debtors)

    if has_multiple_options:
        print(
            f'Выбран вариант подсудности по адресам должников: '
            f'{format_debtor_indexes(debtor_indexes)}.'
        )
    else:
        print('По всем указанным адресам получен один и тот же суд.')

    print_procedure(branch)
    print_court_info(branch, jurisdiction)
    print_court_contacts(jurisdiction)


# Обрабатывает солидарных должников.
def handle_solidary_debtors(
    type_of_energy_resource: str,
    debtor_count: int
) -> None:
    total_debt = input_positive_number(
        'Введите общую сумму задолженности по всем должникам: '
    )

    branch = get_branch(
        debt=total_debt,
        debtor_count=debtor_count,
        liability_type='solidary'
    )

    single_branch = get_single_branch_for_amount(total_debt)

    debtors = []

    for index in range(1, debtor_count + 1):
        print()
        print(f'--- Ввод адреса для должника № {index} ---')

        address_data, jurisdiction = input_address(single_branch)

        debtors.append({
            'index': index,
            'address_data': address_data,
            'jurisdiction': jurisdiction
        })

    options = group_solidary_options(single_branch, debtors)

    if len(options) == 1:
        print_solidary_result(
            type_of_energy_resource=type_of_energy_resource,
            total_debt=total_debt,
            branch=single_branch,
            debtors=debtors,
            selected_option=options[0],
            has_multiple_options=False
        )
        return

    print()
    print('По адресам солидарных должников получены разные допустимые варианты подсудности.')
    print('Выберите подходящий вариант:')

    for option_index, option in enumerate(options, start=1):
        jurisdiction = option['jurisdiction']

        print()
        print(f'Вариант {option_index}.')
        print(f'Должники: {format_debtor_indexes(option["debtors"])}.')

        if single_branch == 'one_debtor_order' and jurisdiction['court_name']:
            print(f'Судебный участок: {jurisdiction["court_name"]}.')

        if single_branch == 'one_debtor_claim' and jurisdiction['court_name']:
            print(f'Районный суд: {jurisdiction["court_name"]}.')

        if jurisdiction['court_address']:
            print(f'Адрес суда: {jurisdiction["court_address"]}.')

    selected_option_index = input_number_in_range(
        f'Введите номер варианта от 1 до {len(options)}: ',
        1,
        len(options)
    )

    selected_option = options[selected_option_index - 1]

    print_solidary_result(
        type_of_energy_resource=type_of_energy_resource,
        total_debt=total_debt,
        branch=single_branch,
        debtors=debtors,
        selected_option=selected_option,
        has_multiple_options=True
    )


# -----------------------------
# Долевые должники
# -----------------------------

# Обрабатывает долевых должников.
def handle_shared_debtors(
    type_of_energy_resource: str,
    debtor_count: int
) -> None:
    shared_data = input_shared_debt_data(debtor_count)

    if shared_data['status'] == 'unknown':
        print()
        print('Не удалось продолжить автоматически.')
        print('Нужно уточнить размер доли каждого должника или сумму по каждому должнику.')
        return

    total_debt = shared_data['total_debt']
    debtor_amounts = shared_data['debtor_amounts']
    share_texts = shared_data['share_texts']
    distribution_comment = shared_data['distribution_comment']

    branch = get_branch(
        debt=total_debt,
        debtor_count=debtor_count,
        liability_type='shared',
        debtor_amounts=debtor_amounts
    )

    print()
    print('Долевые должники.')
    print(f'Количество должников: {debtor_count}.')
    print(f'Общая сумма требования: {format_money(total_debt)} руб.')

    if distribution_comment:
        print(distribution_comment)

    if branch == 'multiple_debtors_shared_order':
        print('У всех должников получается приказное производство.')

    if branch == 'multiple_debtors_shared_claim':
        print('У всех должников получается исковое производство.')

    if branch == 'multiple_debtors_shared_mixed':
        print('Смешанный случай: у части должников приказ, у части иск.')

    for index in range(1, debtor_count + 1):
        debtor_debt = debtor_amounts[index - 1]
        share_text = share_texts[index - 1]
        single_branch = get_single_branch_for_amount(debtor_debt)

        print()
        print(f'--- Ввод адреса для должника № {index} ---')

        address_data, jurisdiction = input_address(single_branch)

        print_single_result(
            type_of_energy_resource=type_of_energy_resource,
            debt=debtor_debt,
            branch=single_branch,
            address_data=address_data,
            jurisdiction=jurisdiction,
            title=f'Результат по должнику № {index}',
            share_text=share_text
        )


# -----------------------------
# Один должник
# -----------------------------

# Отдельный сценарий для одного должника.
def handle_single_debtor(type_of_energy_resource: str) -> None:
    debt = input_positive_number('Введите сумму задолженности: ')
    branch = get_branch(debt=debt, debtor_count=1)

    address_data, jurisdiction = input_address(branch)

    print()
    print('Количество должников: 1.')

    print_single_result(
        type_of_energy_resource=type_of_energy_resource,
        debt=debt,
        branch=branch,
        address_data=address_data,
        jurisdiction=jurisdiction
    )


# -----------------------------
# Главная функция
# -----------------------------

def main():
    type_of_energy_resource = input_resource_type()
    debtor_count = input_positive_number('Введите количество должников: ')

    if debtor_count == 1:
        handle_single_debtor(type_of_energy_resource)
        return

    liability_type = input_liability_type()

    if liability_type == 'unknown':
        print()
        print('Количество должников больше одного.')
        print('Не удалось продолжить автоматически.')
        print('Нужно уточнить, является ли ответственность должников долевой или солидарной.')
        return

    if liability_type == 'solidary':
        handle_solidary_debtors(
            type_of_energy_resource=type_of_energy_resource,
            debtor_count=debtor_count
        )
        return

    handle_shared_debtors(
        type_of_energy_resource=type_of_energy_resource,
        debtor_count=debtor_count
    )


if __name__ == '__main__':
    main()