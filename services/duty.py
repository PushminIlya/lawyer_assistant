# services/duty.py


# -----------------------------
# Константы для расчёта пошлины
# -----------------------------

# Верхние границы диапазонов для имущественных исков
# и параметры расчёта внутри каждого диапазона.
#
# Формат кортежа:
# (
#     верхняя_граница_диапазона,
#     базовая_пошлина_на_нижней_границе,
#     нижняя_граница_диапазона,
#     ставка_на_сумму_сверх_нижней_границы
# )
#
# Пример для диапазона до 300 000:
# 4 000 + 3% от суммы сверх 100 000
PROPERTY_CLAIM_DUTY_BRACKETS = [
    (100_000, 4_000, 0, 0),
    (300_000, 4_000, 100_000, 0.03),
    (500_000, 10_000, 300_000, 0.025),
    (1_000_000, 15_000, 500_000, 0.02),
    (3_000_000, 25_000, 1_000_000, 0.01),
    (8_000_000, 45_000, 3_000_000, 0.007),
    (24_000_000, 80_000, 8_000_000, 0.0035),
    (50_000_000, 136_000, 24_000_000, 0.003),
    (100_000_000, 214_000, 50_000_000, 0.002),
]

# Для сумм свыше 100 000 000 рублей.
OVER_100_MILLION_BASE_DUTY = 314_000
OVER_100_MILLION_THRESHOLD = 100_000_000
OVER_100_MILLION_RATE = 0.0015
MAX_PROPERTY_CLAIM_DUTY = 900_000


# -----------------------------
# Внутренние helper-функции
# -----------------------------

# Считает пошлину внутри конкретного диапазона.
def calculate_bracket_duty(
    amount: int,
    base_duty: int,
    threshold: int,
    rate: float
) -> int:
    # Для первого диапазона ставка нулевая,
    # поэтому просто вернётся фиксированная сумма.
    duty = base_duty + (amount - threshold) * rate
    return int(duty)


# -----------------------------
# Основные функции расчёта
# -----------------------------

# Рассчитывает госпошлину по имущественному требованию,
# подлежащему оценке, для судов общей юрисдикции / мировых судей.
#
# Основа расчёта:
# ст. 333.19 НК РФ, подп. 1 п. 1.
#
# На текущем этапе работаем в целых рублях,
# потому что суммы требования в программе тоже целые.
def calculate_property_claim_duty(amount: int) -> int:
    if amount <= 0:
        return 0

    # Сначала проверяем все стандартные диапазоны.
    for max_amount, base_duty, threshold, rate in PROPERTY_CLAIM_DUTY_BRACKETS:
        if amount <= max_amount:
            return calculate_bracket_duty(
                amount=amount,
                base_duty=base_duty,
                threshold=threshold,
                rate=rate
            )

    # Если сумма больше 100 000 000 рублей,
    # применяется отдельная формула с верхним пределом.
    duty = calculate_bracket_duty(
        amount=amount,
        base_duty=OVER_100_MILLION_BASE_DUTY,
        threshold=OVER_100_MILLION_THRESHOLD,
        rate=OVER_100_MILLION_RATE
    )

    if duty > MAX_PROPERTY_CLAIM_DUTY:
        return MAX_PROPERTY_CLAIM_DUTY

    return duty


# Рассчитывает госпошлину по заявлению о вынесении судебного приказа.
#
# Логика:
# берём 50% от пошлины,
# которая уплачивалась бы при имущественном иске.
def calculate_order_duty(amount: int) -> int:
    claim_duty = calculate_property_claim_duty(amount)
    return int(claim_duty * 0.5)


# Возвращает унифицированный словарь с результатом расчёта.
# Это удобно для main.py и итогового вывода.
def build_duty_result(amount: int, duty_type: str, label: str) -> dict:
    return {
        'amount': amount,
        'type': duty_type,
        'label': label
    }


# Универсальная функция для расчёта госпошлины
# по уже определённой ветке обработки.
def get_duty_info(branch: str, amount: int) -> dict:
    if branch == 'one_debtor_order':
        duty = calculate_order_duty(amount)

        return build_duty_result(
            amount=duty,
            duty_type='court_order',
            label='Госпошлина за заявление о вынесении судебного приказа'
        )

    if branch == 'one_debtor_claim':
        duty = calculate_property_claim_duty(amount)

        return build_duty_result(
            amount=duty,
            duty_type='claim',
            label='Госпошлина за исковое заявление имущественного характера'
        )

    # Для прочих веток пошлина здесь напрямую не считается.
    # Например, для нескольких должников она определяется
    # выше по сценарию main.py: либо по каждому отдельно,
    # либо по общей сумме требования.
    return build_duty_result(
        amount=0,
        duty_type='unknown',
        label='Госпошлина не определена'
    )