import re

from services.data_loader import get_sections_index, load_sheet_rows


# -----------------------------
# Константы
# -----------------------------

# Поддерживаемые ветки обработки.
ONE_DEBTOR_ORDER = 'one_debtor_order'
ONE_DEBTOR_CLAIM = 'one_debtor_claim'
MULTIPLE_DEBTORS = 'multiple_debtors'

# Типы строк правил в Excel.
RULE_TYPE_FULL = 'полностью'
RULE_TYPE_HOUSE_LIST = 'список домов'

# Служебные статусы результата.
STATUS_RESOLVED = 'resolved'
STATUS_NEED_STREET = 'need_street'
STATUS_NEED_HOUSE = 'need_house'
STATUS_INVALID_SETTLEMENT = 'invalid_settlement'
STATUS_INVALID_STREET = 'invalid_street'
STATUS_NOT_FOUND = 'not_found'

# Категории, которые считаем уличными объектами.
# Это нужно, чтобы отличать населённые пункты от улиц,
# когда проверяем корректность ввода населённого пункта.
STREET_OBJECT_CATEGORIES = {
    'улица',
    'переулок',
    'проезд',
    'проспект',
    'бульвар',
    'шоссе',
    'квартал'
}

# Отдельно поддерживаем город Хабаровск как допустимый населённый пункт,
# даже если он не задан единым правилом типа "полностью".
KNOWN_CITY_VARIANTS = {
    'хабаровск',
    'город хабаровск',
    'хабаровск город'
}


# -----------------------------
# Нормализация
# -----------------------------

# Приводит текст к единому виду для сравнения:
# - нижний регистр
# - ё -> е
# - без лишней пунктуации
# - без повторяющихся пробелов
def normalize_text(text: str) -> str:
    text = str(text).lower().strip()
    text = text.replace('ё', 'е')

    text = re.sub(r'[«»"()]', ' ', text)
    text = re.sub(r'[.,;:]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


# Нормализует номер дома.
# Примеры:
# - "дом 15" -> "15"
# - "д. 15" -> "15"
# - "№ 15" -> "15"
# - "107 / 1" -> "107/1"
def normalize_house(text: str) -> str:
    text = normalize_text(text)
    text = text.replace('дом', ' ')
    text = text.replace('д', ' ')
    text = text.replace('№', ' ')
    text = re.sub(r'\s+', '', text)
    return text.strip()


# -----------------------------
# Выбор листа Excel
# -----------------------------

# Определяет, какой лист Excel использовать.
def get_sheet_name(branch: str) -> str:
    if branch == ONE_DEBTOR_ORDER:
        return 'Правила'

    if branch == ONE_DEBTOR_CLAIM:
        return 'Районные суды'

    return ''


# -----------------------------
# Подготовка вариантов для сравнения
# -----------------------------

# Строит варианты записи объекта, который ввёл пользователь.
#
# Для населённого пункта:
# settlement_type = "село", settlement_name = "Мирное"
# -> {"мирное", "село мирное", "мирное село"}
#
# Для улицы:
# street_type = "улица", street_name = "Ленина"
# -> {"ленина", "улица ленина", "ленина улица"}
def build_user_variants(address_data: dict, stage: str) -> set[str]:
    variants = set()

    if stage == 'settlement':
        object_type = normalize_text(address_data.get('settlement_type', ''))
        object_name = normalize_text(address_data.get('settlement_name', ''))
    else:
        object_type = normalize_text(address_data.get('street_type', ''))
        object_name = normalize_text(address_data.get('street_name', ''))

    if not object_name:
        return variants

    variants.add(object_name)

    if object_type:
        variants.add(f'{object_type} {object_name}'.strip())
        variants.add(f'{object_name} {object_type}'.strip())

    return {item for item in variants if item}


# Строит варианты записи объекта из строки Excel.
#
# Пример:
# Категория = "село"
# Адрес / объект = "Мирное"
# -> {"мирное", "село мирное", "мирное село"}
def build_row_variants(row: dict) -> set[str]:
    category = normalize_text(row.get('Категория', ''))
    object_name = normalize_text(row.get('Адрес / объект', ''))

    if not object_name:
        return set()

    variants = {object_name}

    # "адресное правило" — служебная категория,
    # её в текст объекта включать не нужно.
    if category and category != 'адресное правило':
        variants.add(f'{category} {object_name}'.strip())
        variants.add(f'{object_name} {category}'.strip())

    return {item for item in variants if item}


# Проверяет, подходит ли строка Excel под объект пользователя.
def row_matches_component(
    row: dict,
    address_data: dict,
    stage: str,
    expected_rule_type: str
) -> bool:
    rule_type = normalize_text(row.get('Тип', ''))

    if rule_type != normalize_text(expected_rule_type):
        return False

    user_variants = build_user_variants(address_data, stage)
    row_variants = build_row_variants(row)

    if not user_variants or not row_variants:
        return False

    for user_variant in user_variants:
        if user_variant in row_variants:
            return True

    return False


# -----------------------------
# Работа с номерами домов
# -----------------------------

# Извлекает из текста правила отдельные номера домов.
# Поддерживает:
# - число: 15
# - число с буквой: 15а
# - дробный номер: 107/1
def extract_house_tokens(rule_text: str) -> set[str]:
    normalized = normalize_text(rule_text)
    tokens = re.findall(r'\d+[а-яa-z]?(?:/\d+[а-яa-z]?)?', normalized)
    return {normalize_house(token) for token in tokens if token}


# Проверяет, входит ли дом пользователя в правило домов.
# Поддерживаем:
# 1. явный список домов
# 2. простой диапазон "с N по M"
def house_matches_rule(house: str, rule_text: str) -> bool:
    normalized_house = normalize_house(house)

    if not normalized_house:
        return False

    # Сначала пробуем найти дом в явном списке.
    tokens = extract_house_tokens(rule_text)

    if normalized_house in tokens:
        return True

    # Потом пробуем диапазон.
    normalized_rule = normalize_text(rule_text)
    ranges = re.findall(r'с\s*(\d+)\s*по\s*(\d+)', normalized_rule)

    if normalized_house.isdigit():
        house_number = int(normalized_house)

        for start, end in ranges:
            if int(start) <= house_number <= int(end):
                return True

    return False


# -----------------------------
# Поиск по Excel
# -----------------------------

# Ищет совпадение среди строк типа "полностью".
def find_full_match(sheet_name: str, address_data: dict, stage: str) -> dict | None:
    rows = load_sheet_rows(sheet_name)

    for row in rows:
        if row_matches_component(row, address_data, stage, RULE_TYPE_FULL):
            return row

    return None


# Проверяет, существует ли вообще такой населённый пункт.
#
# Это нужно, чтобы отличать:
# - корректный населённый пункт, после которого надо спрашивать улицу
# - опечатку в населённом пункте
def has_supported_settlement(sheet_name: str, address_data: dict) -> bool:
    settlement_variants = build_user_variants(address_data, 'settlement')

    if not settlement_variants:
        return False

    # Специально разрешаем город Хабаровск.
    for variant in settlement_variants:
        if variant in KNOWN_CITY_VARIANTS:
            return True

    rows = load_sheet_rows(sheet_name)

    for row in rows:
        rule_type = normalize_text(row.get('Тип', ''))
        category = normalize_text(row.get('Категория', ''))
        row_variants = build_row_variants(row)

        if rule_type != RULE_TYPE_FULL:
            continue

        # Нас здесь интересуют только населённые пункты, а не улицы.
        if category in STREET_OBJECT_CATEGORIES:
            continue

        if not row_variants:
            continue

        for variant in settlement_variants:
            if variant in row_variants:
                return True

    return False


# Проверяет, существует ли такая улица / объект
# среди строк типа "список домов".
def has_street_in_house_rules(sheet_name: str, address_data: dict) -> bool:
    rows = load_sheet_rows(sheet_name)

    for row in rows:
        if row_matches_component(row, address_data, 'street', RULE_TYPE_HOUSE_LIST):
            return True

    return False


# Ищет совпадение по улице и номеру дома.
def find_house_match(sheet_name: str, address_data: dict) -> dict | None:
    rows = load_sheet_rows(sheet_name)
    house = address_data.get('house', '')

    for row in rows:
        if not row_matches_component(row, address_data, 'street', RULE_TYPE_HOUSE_LIST):
            continue

        rule_text = str(row.get('Правило домов', ''))

        if house_matches_rule(house, rule_text):
            return row

    return None


# -----------------------------
# Сбор результата
# -----------------------------

# Собирает красивое название совпавшего объекта.
def build_matched_object(row: dict) -> str:
    category = str(row.get('Категория', '')).strip()
    object_name = str(row.get('Адрес / объект', '')).strip()

    if not category or category.lower() == 'адресное правило':
        return object_name

    return f'{category} {object_name}'.strip()


# Возвращает базовый словарь результата.
# Дальше он будет дополняться конкретными полями.
def build_base_result(
    status: str,
    court_level: str,
    document_type: str,
    comment: str
) -> dict:
    return {
        'status': status,
        'court_level': court_level,
        'document_type': document_type,
        'court_name': '',
        'section_number': None,
        'district_court': '',
        'matched_address': '',
        'court_address': '',
        'court_phones': '',
        'court_email': '',
        'court_url': '',
        'comment': comment
    }


# Строит базовый результат по ветке.
def build_branch_result(branch: str, status: str, comment: str) -> dict:
    if branch == ONE_DEBTOR_ORDER:
        return build_base_result(
            status=status,
            court_level='мировой судья',
            document_type='заявление о вынесении судебного приказа',
            comment=comment
        )

    if branch == ONE_DEBTOR_CLAIM:
        return build_base_result(
            status=status,
            court_level='районный суд',
            document_type='исковое заявление',
            comment=comment
        )

    return build_base_result(
        status=status,
        court_level='не определено',
        document_type='не определено',
        comment=comment
    )


# Собирает итоговый успешный результат.
def build_resolved_result(branch: str, row: dict, match_kind: str) -> dict:
    matched_object = build_matched_object(row)

    if match_kind == 'settlement_full':
        comment = 'Подсудность определена сразу по населённому пункту.'
    elif match_kind == 'street_full':
        comment = 'Подсудность определена сразу по объекту целиком.'
    else:
        comment = 'Подсудность определена по объекту и номеру дома.'

    if branch == ONE_DEBTOR_ORDER:
        section_number = row.get('Участок')
        sections_index = get_sections_index()
        section_info = sections_index.get(section_number, {})

        result = build_branch_result(branch, STATUS_RESOLVED, comment)
        result.update({
            'court_name': row.get('Заголовок секции', ''),
            'section_number': section_number,
            'district_court': section_info.get('Районный суд', ''),
            'matched_address': matched_object,
            'court_address': section_info.get('Адрес участка', ''),
            'court_phones': section_info.get('Телефоны участка', ''),
            'court_email': section_info.get('E-mail участка', ''),
            'court_url': section_info.get('Офиц. страница участка', '')
        })
        return result

    district_court = row.get('Районный суд', '') or row.get('Заголовок секции', '')

    result = build_branch_result(branch, STATUS_RESOLVED, comment)
    result.update({
        'court_name': district_court,
        'district_court': district_court,
        'matched_address': matched_object,
        'court_address': row.get('Адрес райсуда', ''),
        'court_phones': row.get('Телефоны райсуда', ''),
        'court_email': row.get('E-mail райсуда', ''),
        'court_url': row.get('Офиц. страница райсуда', '')
    })
    return result


# Населённого пункта недостаточно, нужна улица.
def build_need_street_result(branch: str) -> dict:
    return build_branch_result(
        branch=branch,
        status=STATUS_NEED_STREET,
        comment='Населённого пункта недостаточно. Нужна улица или иной объект.'
    )


# Населённый пункт не найден.
def build_invalid_settlement_result(branch: str) -> dict:
    return build_branch_result(
        branch=branch,
        status=STATUS_INVALID_SETTLEMENT,
        comment='Населённый пункт не найден. Проверьте ввод и попробуйте снова.'
    )


# Улицы недостаточно, нужен дом.
def build_need_house_result(branch: str) -> dict:
    return build_branch_result(
        branch=branch,
        status=STATUS_NEED_HOUSE,
        comment='Улицы недостаточно. Нужен номер дома.'
    )


# Улица / объект не найдены.
def build_invalid_street_result(branch: str) -> dict:
    return build_branch_result(
        branch=branch,
        status=STATUS_INVALID_STREET,
        comment='Улица или иной объект не найдены. Проверьте ввод и попробуйте снова.'
    )


# Подсудность не определилась.
def build_not_found_result(branch: str) -> dict:
    return build_branch_result(
        branch=branch,
        status=STATUS_NOT_FOUND,
        comment='Не удалось определить подсудность по введённым данным.'
    )


# -----------------------------
# Главная функция
# -----------------------------

# Определяет подсудность по ветке и адресу.
#
# Схема:
# 1. несколько должников -> возвращаем отдельную заглушку;
# 2. пробуем определить суд сразу по населённому пункту;
# 3. если населённый пункт некорректен -> invalid_settlement;
# 4. если населённый пункт корректен, но его мало -> need_street;
# 5. пробуем определить суд по улице / объекту;
# 6. если улица некорректна -> invalid_street;
# 7. если улица корректна, но нужен дом -> need_house;
# 8. ищем по дому;
# 9. если не нашли -> not_found.
def get_jurisdiction(branch: str, address_data: dict) -> dict:
    if branch == MULTIPLE_DEBTORS:
        return build_base_result(
            status=STATUS_RESOLVED,
            court_level='требуется уточнение',
            document_type='зависит от состава должников',
            comment=(
                'Для нескольких должников нужно отдельно определить '
                'адрес каждого должника и правила подсудности.'
            )
        )

    sheet_name = get_sheet_name(branch)

    if not sheet_name:
        return build_not_found_result(branch)

    # Шаг 1. Пытаемся определить суд сразу по населённому пункту.
    settlement_match = find_full_match(sheet_name, address_data, 'settlement')

    if settlement_match:
        return build_resolved_result(branch, settlement_match, 'settlement_full')

    # Если населённый пункт вообще не поддерживается,
    # считаем это ошибкой ввода.
    settlement_exists = has_supported_settlement(sheet_name, address_data)

    if not settlement_exists:
        return build_invalid_settlement_result(branch)

    # Если улицу ещё не ввели, дальше двигаться рано.
    if not address_data.get('street_name'):
        return build_need_street_result(branch)

    # Шаг 2. Пытаемся определить суд сразу по улице / объекту.
    street_match = find_full_match(sheet_name, address_data, 'street')

    if street_match:
        return build_resolved_result(branch, street_match, 'street_full')

    # Если улица не подошла как "полностью", проверяем,
    # существует ли она вообще в строках со списком домов.
    street_exists = has_street_in_house_rules(sheet_name, address_data)

    if not street_exists:
        return build_invalid_street_result(branch)

    # Если улица существует, но дом ещё не ввели,
    # просим ввести дом.
    if not address_data.get('house'):
        return build_need_house_result(branch)

    # Шаг 3. Ищем по улице и номеру дома.
    house_match = find_house_match(sheet_name, address_data)

    if house_match:
        return build_resolved_result(branch, house_match, 'house_list')

    return build_not_found_result(branch)