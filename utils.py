from email.mime.text import MIMEText
from random import randrange
from smtplib import SMTP_SSL

from db_connection import select_alias
from models import Account, DynamicQueryData, QueryData
from settings import SENDER_EMAIL, HOST, PORT, PASSWORD, SUBJECT


def home_keys(func):
    return [
        [func('Add Expense', QueryData.ADD_EXPENSE)],
        [func('History', QueryData.HISTORY), func('Change Account', QueryData.CHANGE_ACCOUNT)],
        [func('About', QueryData.ABOUT), func('Help', QueryData.HELP)]
    ]


def change_account_keys(func):
    return [
        [func('Back', QueryData.BACK)],
        [func('About', QueryData.ABOUT), func('Help', QueryData.HELP)]]


def about_help_keys(func):
    return [
        [func('About', QueryData.ABOUT), func('Help', QueryData.HELP)]
    ]


def split_by_keys(func):
    return [
        [func('Equally', QueryData.EQUALLY), func('Exact amount', QueryData.EXACT_AMOUNT)],
        [func('Percentage', QueryData.PERCENTAGE), func('Share', QueryData.SHARE)]
    ]


def get_aliases(func, group_id, user_id=None, alias_count=None):
    buttons = []
    if user_id:
        if type(alias_count) != dict:
            alias_count = dict()
        for _, alias, cost in select_alias(group_id):
            count = alias_count.get(alias, '0')
            buttons.append([
                func(f"{alias}: {cost}",
                     f"{DynamicQueryData.ALIAS}{user_id}_{alias}{DynamicQueryData.ENTER_AMOUNT}"),
                func(count,
                     f"{DynamicQueryData.ALIAS}{user_id}_{alias}{DynamicQueryData.ENTER_AMOUNT}"),
                func('⬆️', f"{DynamicQueryData.ALIAS}{user_id}_{alias}{DynamicQueryData.PLUS}"),
                func('⬇️', f"{DynamicQueryData.ALIAS}{user_id}_{alias}{DynamicQueryData.MINUS}")
            ])
        buttons.extend([
            [func('Add alias', f'{QueryData.ADD_ALIAS}{user_id}'),
             func('Edit alias', f'{QueryData.EDIT_ALIAS}{user_id}'),
             func('Delete alias', f'{QueryData.DELETE_ALIAS}{user_id}')],
            [func('Continue', QueryData.CONTINUE_ALIAS)]])
    else:
        for _, alias, cost in select_alias(group_id):
            buttons.append(
                [func(f"{alias}: {cost}", f"{DynamicQueryData.ALIAS}{alias}{DynamicQueryData.EDIT}")])
    return buttons


def send_email(to_email, chat_acc: Account):
    code = randrange(100000, 1000000)
    body = f'Verification code from Splitwise bot:\n\n{code}'
    msg = MIMEText(body)
    msg['Subject'] = SUBJECT
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    try:
        with SMTP_SSL(HOST, PORT) as smtp_server:
            smtp_server.login(SENDER_EMAIL, PASSWORD)
            smtp_server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())
    except:  # noqa
        return False
    chat_acc.verification.code = code
    return True


def expense_details(func, chat_acc):
    return [
        [func(f'Group: {chat_acc.expense.selected_group_name}', QueryData.ADD_EXPENSE)],
        [func(f'Description: {chat_acc.expense.description}', QueryData.DESCRIPTION)],
        [func(f'Amount: {chat_acc.expense.amount}', QueryData.AMOUNT)],
        [func(f'Currency: {chat_acc.expense.currency}', QueryData.CURRENCY)],
        [func(f'Split by: {chat_acc.expense.split_type}', QueryData.SPLIT_BY)],
        [func('Cancel', QueryData.BACK), func('Submit', QueryData.SUBMIT)]
    ]
