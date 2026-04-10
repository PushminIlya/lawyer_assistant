from services.branching import get_branch
from services.jurisdiction import get_jurisdiction


def main():
    resource_choice = ''
    type_of_energy_resource = ''

    while resource_choice not in ('1', '2'):
        resource_choice = input(
            'Введите вид ресурса (электроэнергия - 1, теплоэнергия - 2): '
        ).strip()

        if not resource_choice.isdigit():
            print('Ошибка ввода. Выберите вид ресурса из предложенных.')
            continue

        if resource_choice not in ('1', '2'):
            print('Ошибка ввода. Выберите вид ресурса из предложенных.')

    if resource_choice == '1':
        type_of_energy_resource = 'электроэнергия'
    else:
        type_of_energy_resource = 'теплоэнергия'

    debt = 0

    while True:
        debt_input = input('Введите сумму задолженности: ').strip()

        if not debt_input.isdigit():
            print('Ошибка ввода. Сумма задолженности должна быть положительным числом.')
            continue

        debt = int(debt_input)

        if debt <= 0:
            print('Ошибка ввода. Сумма задолженности должна быть больше нуля.')
            continue

        break

    debtor = 0

    while True:
        debtor_input = input('Введите количество должников: ').strip()

        if not debtor_input.isdigit():
            print('Ошибка ввода. Количество должников должно быть положительным числом.')
            continue

        debtor = int(debtor_input)

        if debtor <= 0:
            print('Ошибка ввода. Количество должников должно быть больше нуля.')
            continue

        break

    debtor_address = input('Введите адрес должника: ').strip()

    branch = get_branch(debt, debtor)
    jurisdiction = get_jurisdiction(branch, debtor_address)



    print()
    print(f'Задолженность за ресурс: {type_of_energy_resource}.')
    print(f'Количество должников: {debtor}.')
    print(f'Сумма задолженности: {debt}.')
    print(f'Адрес должника: {debtor_address}.')

    if branch:
        print(f'Выбрана ветка: {branch}.')
        print(f'Уровень суда: {jurisdiction["court_level"]}.')
        print(f'Форма обращения: {jurisdiction["document_type"]}.')
        print(f'Комментарий: {jurisdiction["comment"]}')


if __name__ == '__main__':
    main()









