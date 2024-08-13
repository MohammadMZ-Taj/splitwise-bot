from datetime import datetime, timedelta
from email.mime.text import MIMEText
from random import randrange
from smtplib import SMTP_SSL

from pyrogram import Client
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from db_connection import select_user, add_user, delete_user
from models import Account, QueryData, Status, ExpenseStatus, SplitShare
from settings import PROXY, BOT_NAME, BOT_TOKEN, SENDER_EMAIL, HOST, PORT, PASSWORD, SUBJECT
from splitwise_connection import search_user, get_groups, get_members_equally, get_members_exact_amount, \
    get_members_percentage, get_members_share

if not PROXY:
    client = Client(name=BOT_NAME, bot_token=BOT_TOKEN)
else:
    client = Client(name=BOT_NAME, bot_token=BOT_TOKEN, proxy=PROXY)

chatId_account = dict()

home = InlineKeyboardMarkup([
    [InlineKeyboardButton('Add Expense', QueryData.ADD_EXPENSE)],
    [InlineKeyboardButton('History', QueryData.HISTORY),
     InlineKeyboardButton('Change Account', QueryData.CHANGE_ACCOUNT)],
    [InlineKeyboardButton('About', QueryData.ABOUT), InlineKeyboardButton('Help', QueryData.HELP)]
])

change_account = InlineKeyboardMarkup([
    [InlineKeyboardButton('Back', QueryData.BACK)],
    [InlineKeyboardButton('About', QueryData.ABOUT), InlineKeyboardButton('Help', QueryData.HELP)]])

about_help = InlineKeyboardMarkup([
    [InlineKeyboardButton('About', QueryData.ABOUT), InlineKeyboardButton('Help', QueryData.HELP)]
])

split_by = InlineKeyboardMarkup([
    [InlineKeyboardButton('Equally', QueryData.EQUALLY), InlineKeyboardButton('Exact amount', QueryData.EXACT_AMOUNT)],
    [InlineKeyboardButton('Percentage', QueryData.PERCENTAGE), InlineKeyboardButton('Share', QueryData.SHARE)]
])


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


def expense_details(chat_acc):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f'Group: {chat_acc.expense.selected_group_name}', QueryData.ADD_EXPENSE)],
        [InlineKeyboardButton(f'Description: {chat_acc.expense.description}', QueryData.DESCRIPTION)],
        [InlineKeyboardButton(f'Amount: {chat_acc.expense.amount}', QueryData.AMOUNT)],
        [InlineKeyboardButton(f'Currency: {chat_acc.expense.currency}', QueryData.CURRENCY)],
        [InlineKeyboardButton(f'Split by: {chat_acc.expense.split_type}', QueryData.SPLIT_BY)],
        [InlineKeyboardButton('Cancel', QueryData.BACK), InlineKeyboardButton('Submit', QueryData.SUBMIT)]
    ])


@client.on_message()
def handle_message(bot: Client, message: Message):  # noqa
    chat_id = message.chat.id
    msg = message.text
    if msg:
        if msg.startswith('/start'):
            if acc := chatId_account.get(chat_id, None):
                name, email, _ = search_user(user_id=acc.account_id)
                acc.email = email
                bot.send_message(chat_id, f'Hi {name}\nWelcome to splitwise!\n\n'
                                          f'Be aware that you must have added me to your splitwise groups',
                                 reply_markup=home)
            else:
                bot.send_message(chat_id, f'Welcome to splitwise!\n\nFirst add me to your splitwise groups\n'
                                          f'Then enter your email here to verify', reply_markup=about_help)
                chatId_account[chat_id] = Account()
        else:
            chat_acc = chatId_account[chat_id]
            if chat_acc.status in [Status.START, Status.CHANGE_EMAIL]:
                if send_email(msg, chat_acc):
                    ch_mail = ''
                    if chat_acc.status == Status.CHANGE_EMAIL:
                        ch_mail = 'Your previous account has been deleted\n\n'
                        delete_user(chat_acc.account_id)
                    chat_acc.status = Status.SEND_EMAIL
                    chat_acc.email = msg
                    chat_acc.verification.is_verify = False
                    chat_acc.verification.start_time = datetime.now()
                    bot.send_message(chat_id, ch_mail + 'Check your email and enter Verification code here:\n'
                                                        '(You have 3 chances and 2 minutes)')
                else:
                    bot.send_message(chat_id, 'Something went wrong!\nEnter your email again',
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Back',
                                                                                              QueryData.BACK)]]) if chat_acc.status == Status.CHANGE_EMAIL else None)
            elif chat_acc.status == Status.SEND_EMAIL and not chat_acc.verification.is_verify:
                if chat_acc.verification.chance and chat_acc.verification.start_time + timedelta(
                        minutes=2) >= datetime.now():
                    chat_acc.verification.chance -= 1
                    if msg.isdigit() and int(msg) == chat_acc.verification.code:
                        name, _, acc_id = search_user(email=chat_acc.email)
                        add_user(chat_id, acc_id, chat_acc.email)
                        chat_acc.account_id = acc_id
                        chat_acc.verification.is_verify = True
                        bot.send_message(chat_id, f'Hi {name}\nWelcome to splitwise!', reply_markup=home)
                    else:
                        if chat_acc.verification.chance:
                            bot.send_message(chat_id, f'Wrong code.\nYou have {chat_acc.verification.chance} chances')
                        else:
                            bot.send_message(chat_id, f"Wrong code.\nYou have no chance\n\nEnter your email again:")
                            chat_acc.status = Status.START
                            chat_acc.verification.chance = 3
                else:
                    bot.send_message(chat_id, 'Enter your email again:')
                    chat_acc.status = Status.START
                    chat_acc.verification.chance = 3
            elif chat_acc.verification.is_verify:
                if chat_acc.status == QueryData.DESCRIPTION:
                    chat_acc.expense.description = msg
                    bot.send_message(chat_id, text='Set Details of expense', reply_markup=expense_details(chat_acc))
                elif chat_acc.status == QueryData.AMOUNT:
                    if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                        chat_acc.expense.amount = msg
                        bot.send_message(chat_id, text='Set Details of expense', reply_markup=expense_details(chat_acc))
                        chat_acc.status = None
                    else:
                        bot.send_message(chat_id, 'invalid number\nEnter amount again:')
                elif chat_acc.status.startswith('ua'):
                    if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                        u_id = chat_acc.status[2:chat_acc.status.find('_')]
                        chat_acc.expense.split_share[u_id] = chat_acc.expense.split_share.get(u_id, SplitShare())
                        chat_acc.expense.split_share[u_id].paid_share = msg
                        bot.send_message(chat_id, text='Select users and enter amounts:',
                                         reply_markup=InlineKeyboardMarkup(
                                             get_members_exact_amount(chat_acc.expense.selected_group_id,
                                                                      InlineKeyboardButton,
                                                                      chat_acc.expense.split_share) + [
                                                 [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                        chat_acc.status = None
                    else:
                        bot.send_message(chat_id, 'invalid number\nEnter amount again:')
                elif chat_acc.status.startswith('up') and chat_acc.status.endswith('e'):
                    if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                        u_id = chat_acc.status[2:chat_acc.status.find('_')]
                        chat_acc.expense.split_share[u_id] = chat_acc.expense.split_share.get(u_id, SplitShare())
                        chat_acc.expense.split_share[u_id].paid_share = msg + ' %'
                        bot.send_message(chat_id, text='Select users and enter amounts:',
                                         reply_markup=InlineKeyboardMarkup(
                                             get_members_percentage(chat_acc.expense.selected_group_id,
                                                                    InlineKeyboardButton,
                                                                    chat_acc.expense.split_share) + [
                                                 [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                        chat_acc.status = None
                    else:
                        bot.send_message(chat_id, 'invalid number\nEnter amount again:')
                elif chat_acc.status.startswith('us') and chat_acc.status.endswith('e'):
                    if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                        u_id = chat_acc.status[2:chat_acc.status.find('_')]
                        chat_acc.expense.split_share[u_id] = chat_acc.expense.split_share.get(u_id, SplitShare())
                        chat_acc.expense.split_share[u_id].paid_share = msg
                        bot.send_message(chat_id, text='Select users and enter amounts:',
                                         reply_markup=InlineKeyboardMarkup(
                                             get_members_share(chat_acc.expense.selected_group_id,
                                                                    InlineKeyboardButton,
                                                                    chat_acc.expense.split_share) + [
                                                 [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                        chat_acc.status = None
                    else:
                        bot.send_message(chat_id, 'invalid number\nEnter amount again:')
            else:
                bot.send_message(chat_id, 'invalid message')


@client.on_callback_query()
def handle_callback_query(bot: Client, query: CallbackQuery):  # noqa
    chat_id = query.message.chat.id
    msg_id = query.message.id
    query_data = query.data
    chat_acc = chatId_account[chat_id]
    if chat_acc.verification.is_verify:
        if query_data == QueryData.CHANGE_ACCOUNT:
            bot.edit_message_text(chat_id, message_id=msg_id,
                                  text='First add me to your splitwise groups\nThen enter your email here to verify',
                                  reply_markup=change_account)
            chat_acc.status = Status.CHANGE_EMAIL
        elif query_data == QueryData.BACK:
            chat_acc.expense = ExpenseStatus()
            bot.edit_message_text(chat_id, message_id=msg_id, text='Choose an option', reply_markup=home)
        elif query_data == QueryData.ADD_EXPENSE:
            group_keys = []
            i = 0
            for key in get_groups(chat_acc.account_id, InlineKeyboardButton):
                if i % 3 == 0:
                    group_keys.append([])
                group_keys[-1].append(key)
                i += 1
            group_keys.append([InlineKeyboardButton('Back', QueryData.BACK)])
            bot.edit_message_text(chat_id, message_id=msg_id, text='Select your group:',
                                  reply_markup=InlineKeyboardMarkup(group_keys))
        elif query_data.startswith('g'):
            g_id, g_name = query_data[1:query_data.find('_')], query_data[query_data.find('_') + 1:]
            chat_acc.expense.selected_group_id = int(g_id)
            chat_acc.expense.selected_group_name = g_name
            bot.edit_message_text(chat_id, message_id=msg_id, text='Set Details of expense',
                                  reply_markup=expense_details(chat_acc))
        elif query_data == QueryData.DESCRIPTION:
            chat_acc.status = QueryData.DESCRIPTION
            bot.edit_message_text(chat_id, message_id=msg_id, text='Enter Description:')
        elif query_data == QueryData.AMOUNT:
            chat_acc.status = QueryData.AMOUNT
            bot.edit_message_text(chat_id, message_id=msg_id, text='Enter Amount:')
        elif query_data == QueryData.CURRENCY:
            chat_acc.expense.currency = 'IRR' if chat_acc.expense.currency == 'USD' else 'USD'
            bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=expense_details(chat_acc))
        elif query_data == QueryData.SPLIT_BY:
            bot.edit_message_text(chat_id, message_id=msg_id, text='Split by:', reply_markup=split_by)
        elif chat_acc.expense.selected_group_id:
            if query_data == QueryData.EQUALLY:
                chat_acc.expense.split_type = 'EQUALLY'
                if not chat_acc.expense.split_share:
                    chat_acc.expense.split_share.update({str(chat_acc.account_id): SplitShare('✅')})
                bot.edit_message_text(chat_id, message_id=msg_id, text='Select users:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_members_equally(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                                              chat_acc.expense.split_share) + [
                                              [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
            elif query_data == QueryData.EXACT_AMOUNT:
                chat_acc.expense.split_type = 'EXACT AMOUNT'
                if not chat_acc.expense.split_share:
                    chat_acc.expense.split_share.update(
                        {str(chat_acc.account_id): SplitShare(chat_acc.expense.amount)})
                bot.edit_message_text(chat_id, message_id=msg_id, text='Select users and enter amounts:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_members_exact_amount(chat_acc.expense.selected_group_id,
                                                                   InlineKeyboardButton,
                                                                   chat_acc.expense.split_share) + [
                                              [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
            elif query_data == QueryData.PERCENTAGE:
                chat_acc.expense.split_type = 'PERCENTAGE'
                if not chat_acc.expense.split_share:
                    chat_acc.expense.split_share.update({str(chat_acc.account_id): SplitShare('100 %')})
                bot.edit_message_text(chat_id, message_id=msg_id, text='Select users and enter values:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_members_percentage(chat_acc.expense.selected_group_id,
                                                                 InlineKeyboardButton, chat_acc.expense.split_share) + [
                                              [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
            elif query_data == QueryData.SHARE:
                chat_acc.expense.split_type = 'SHARE'
                if not chat_acc.expense.split_share:
                    chat_acc.expense.split_share.update({str(chat_acc.account_id): SplitShare('1')})
                bot.edit_message_text(chat_id, message_id=msg_id, text='Select users and enter values:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_members_share(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                                            chat_acc.expense.split_share) + [
                                              [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
            elif query_data.startswith('ue'):
                u_id = query_data[2:]
                if not chat_acc.expense.split_share.pop(u_id, None):
                    chat_acc.expense.split_share.update({u_id: SplitShare('✅')})
                bot.edit_message_text(chat_id, message_id=msg_id, text='Select users:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_members_equally(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                                              chat_acc.expense.split_share) + [
                                              [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
            elif query_data.startswith('ua'):
                chat_acc.status = query_data
                u_name = query_data[query_data.find('_') + 1:]
                bot.edit_message_text(chat_id, message_id=msg_id, text=f'Enter amount for {u_name}:')
            elif query_data.startswith('up'):
                if query_data.endswith('p'):
                    u_id = query_data[2:query_data.find('_')]
                    chat_acc.expense.split_share[u_id] = chat_acc.expense.split_share.get(u_id, SplitShare('0 %'))
                    amount = int(chat_acc.expense.split_share.get(u_id).paid_share.split()[0])
                    if amount < 100:
                        chat_acc.expense.split_share[u_id].paid_share = str(amount + 1) + ' %'
                        bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(
                            get_members_percentage(chat_acc.expense.selected_group_id,
                                                   InlineKeyboardButton, chat_acc.expense.split_share) + [
                                [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                elif query_data.endswith('m'):
                    u_id = query_data[2:query_data.find('_')]
                    chat_acc.expense.split_share[u_id] = chat_acc.expense.split_share.get(u_id, SplitShare('0 %'))
                    amount = int(chat_acc.expense.split_share.get(u_id).paid_share.split()[0])
                    if 0 < amount:
                        chat_acc.expense.split_share[u_id].paid_share = str(amount - 1) + ' %'
                        bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(
                            get_members_percentage(chat_acc.expense.selected_group_id,
                                                   InlineKeyboardButton, chat_acc.expense.split_share) + [
                                [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                else:
                    chat_acc.status = query_data
                    u_name = query_data[query_data.find('_') + 1:-1]
                    bot.edit_message_text(chat_id, message_id=msg_id, text=f'Enter percent for {u_name}:')
            elif query_data.startswith('us'):
                if query_data.endswith('p'):
                    u_id = query_data[2:query_data.find('_')]
                    chat_acc.expense.split_share[u_id] = chat_acc.expense.split_share.get(u_id, SplitShare())
                    amount = int(chat_acc.expense.split_share.get(u_id).paid_share.split()[0])
                    chat_acc.expense.split_share[u_id].paid_share = str(amount + 1)
                    bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(
                        get_members_share(chat_acc.expense.selected_group_id,
                                               InlineKeyboardButton, chat_acc.expense.split_share) + [
                            [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                elif query_data.endswith('m'):
                    u_id = query_data[2:query_data.find('_')]
                    chat_acc.expense.split_share[u_id] = chat_acc.expense.split_share.get(u_id, SplitShare())
                    amount = int(chat_acc.expense.split_share.get(u_id).paid_share.split()[0])
                    if 0 < amount:
                        chat_acc.expense.split_share[u_id].paid_share = str(amount - 1)
                        bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(
                            get_members_share(chat_acc.expense.selected_group_id,
                                                   InlineKeyboardButton, chat_acc.expense.split_share) + [
                                [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                else:
                    chat_acc.status = query_data
                    u_name = query_data[query_data.find('_') + 1:-1]
                    bot.edit_message_text(chat_id, message_id=msg_id, text=f'Enter share value for {u_name}:')
    else:
        bot.send_message(chat_id, "You aren't verify yet\n\nFirst add me to your splitwise groups\n"
                                  "Then enter your email here to verify")
        chat_acc.status = Status.START


for rec in select_user():
    chatId_account[rec[0]] = Account(rec[1], rec[2])
    chatId_account[rec[0]].verification.is_verify = True

client.run()
