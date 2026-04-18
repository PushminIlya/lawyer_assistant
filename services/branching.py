# services/branching.py


# -----------------------------
# Константы веток обработки
# -----------------------------

ONE_DEBTOR_ORDER = 'one_debtor_order'
ONE_DEBTOR_CLAIM = 'one_debtor_claim'

MULTIPLE_DEBTORS_UNKNOWN = 'multiple_debtors_unknown'

MULTIPLE_DEBTORS_SOLIDARY_ORDER = 'multiple_debtors_solidary_order'
MULTIPLE_DEBTORS_SOLIDARY_CLAIM = 'multiple_debtors_solidary_claim'

MULTIPLE_DEBTORS_SHARED_ORDER = 'multiple_debtors_shared_order'
MULTIPLE_DEBTORS_SHARED_CLAIM = 'multiple_debtors_shared_claim'
MULTIPLE_DEBTORS_SHARED_MIXED = 'multiple_debtors_shared_mixed'


# -----------------------------
# Внутренние helper-функции
# -----------------------------

# Для одной суммы определяет:
# укладывается ли требование в приказной порядок
# или уже нужен иск.
def get_single_debtor_branch_by_amount(amount: int) -> str:
    if amount <= 500_000:
        return ONE_DEBTOR_ORDER

    return ONE_DEBTOR_CLAIM


# Проверяет, есть ли среди сумм такие,
# которые идут в приказной порядок.
def has_order_amounts(amounts: list[int]) -> bool:
    for amount in amounts:
        if get_single_debtor_branch_by_amount(amount) == ONE_DEBTOR_ORDER:
            return True

    return False


# Проверяет, есть ли среди сумм такие,
# которые требуют искового порядка.
def has_claim_amounts(amounts: list[int]) -> bool:
    for amount in amounts:
        if get_single_debtor_branch_by_amount(amount) == ONE_DEBTOR_CLAIM:
            return True

    return False


# -----------------------------
# Основная функция
# -----------------------------

# Определяет ветку обработки дела.
#
# Логика:
# 1. Если должник один:
#    - до 500000 -> приказ
#    - свыше 500000 -> иск
#
# 2. Если должников несколько:
#    - сначала смотрим вид ответственности:
#      * долевая
#      * солидарная
#      * не знаю
#
# 3. Для долевой ответственности важна сумма по каждому должнику,
#    потому что у разных должников может получиться разный порядок обращения:
#    у одного приказ, у другого иск.
def get_branch(
    debt: int,
    debtor_count: int,
    liability_type: str = '',
    debtor_amounts: list[int] | None = None
) -> str:
    # --- Один должник ---
    if debtor_count == 1:
        return get_single_debtor_branch_by_amount(debt)

    # --- Несколько должников, но тип ответственности не уточнён ---
    if liability_type == 'unknown':
        return MULTIPLE_DEBTORS_UNKNOWN

    # --- Несколько должников, солидарная ответственность ---
    # Здесь ориентируемся на общую сумму требования.
    if liability_type == 'solidary':
        if debt <= 500_000:
            return MULTIPLE_DEBTORS_SOLIDARY_ORDER

        return MULTIPLE_DEBTORS_SOLIDARY_CLAIM

    # --- Несколько должников, долевая ответственность ---
    # Здесь обязательны суммы по каждому должнику.
    if liability_type == 'shared':
        if not debtor_amounts:
            return MULTIPLE_DEBTORS_UNKNOWN

        order_exists = has_order_amounts(debtor_amounts)
        claim_exists = has_claim_amounts(debtor_amounts)

        # Все доли укладываются в приказной порядок.
        if order_exists and not claim_exists:
            return MULTIPLE_DEBTORS_SHARED_ORDER

        # Все доли требуют искового порядка.
        if claim_exists and not order_exists:
            return MULTIPLE_DEBTORS_SHARED_CLAIM

        # Смешанный случай:
        # часть должников идёт в приказ,
        # часть — в иск.
        if order_exists and claim_exists:
            return MULTIPLE_DEBTORS_SHARED_MIXED

    return ''