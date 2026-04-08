from services.branching import get_branch

resource_choice = ''
type_of_energy_resource = ''

while resource_choice not in ('1', '2'):    #Определяем вид энергоресурса
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


debt_input = ''
debt = 0

while True:                                                  #Определяем сумму задолженности
    debt_input = input('Введите сумму задолженности: ').strip()

    if not debt_input.isdigit():
        print('Ошибка ввода. Сумма задолженности должна быть положительным числом.')
        continue

    debt = int(debt_input)

    if debt <= 0:
        print('Ошибка ввода. Сумма задолженности должна быть больше нуля.')
        continue

    break


debtor_input = ''
debtor = 0

while True:                                                      #Определяем количество должников
    debtor_input = input('Введите количество должников: ').strip()

    if not debtor_input.isdigit():
        print('Ошибка ввода. Количество должников должно быть положительным числом.')
        continue

    debtor = int(debtor_input)

    if debtor <= 0:
        print('Ошибка ввода. Количество должников должно быть больше нуля.')
        continue

    break

branch = get_branch(debt, debtor)
# branch = ''
#
# if debtor == 1:
#     if debt <= 500000:
#         branch = 'one_debtor_order'
#     else:
#         branch = 'one_debtor_claim'
# elif debtor > 1:
#     branch = 'multiple_debtors'


print(f'Задолженность за ресурс: {type_of_energy_resource}.')
print(f'Количество должников: {debtor}.')
print(f'Сумма задолженности: {debt}.')

if branch != '':
    print(f'Выбрана ветка: {branch}.')










