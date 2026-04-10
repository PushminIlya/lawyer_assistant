def get_jurisdiction(branch: str, debtor_address: str) -> dict:
    if branch == 'one_debtor_order':
        return {
            'court_level': 'мировой судья',
            'document_type': 'заявление о вынесении судебного приказа',
            'comment': f'Нужно определить судебный участок по адресу должника: {debtor_address}.'
        }

    if branch == 'one_debtor_claim':
        return {
            'court_level': 'районный суд',
            'document_type': 'исковое заявление',
            'comment': f'Нужно определить районный суд по адресу должника: {debtor_address}.'
        }

    if branch == 'multiple_debtors':
        return {
            'court_level': 'требуется уточнение',
            'document_type': 'зависит от состава должников',
            'comment': f'Для нескольких должников нужно отдельно определить адреса и правила подсудности. Текущий адрес: {debtor_address}.'
        }

    return {
        'court_level': 'не определено',
        'document_type': 'не определено',
        'comment': 'Не удалось определить подсудность.'
    }