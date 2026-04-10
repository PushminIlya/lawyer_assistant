def get_branch(debt: int, debtor: int) -> str:
    if debtor == 1:
        if debt <= 500000:
            return 'one_debtor_order'
        return 'one_debtor_claim'

    if debtor > 1:
        return 'multiple_debtors'

    return ''