from datetime import datetime, timedelta

from pyrogram import Client
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from splitwise import Expense
from splitwise.user import ExpenseUser

from db_connection import select_user, add_user, delete_user, select_alias, add_alias, delete_alias, update_alias
from models import Account, QueryData, Status, ExpenseStatus, DynamicQueryData, Alias
from settings import PROXY, BOT_NAME, BOT_TOKEN
from splitwise_connection import search_user, get_groups, get_members_equally, get_members_exact_amount, \
    get_members_percentage, get_members_share, get_user_name, get_members_paid, get_group_name, sObj
from utils import send_email, expense_details, get_aliases, home_keys, about_help_keys, change_account_keys, \
    split_by_keys

if not PROXY:
    client = Client(name=BOT_NAME, bot_token=BOT_TOKEN)
else:
    client = Client(name=BOT_NAME, bot_token=BOT_TOKEN, proxy=PROXY)

chatId_account = dict()


@client.on_message()
def handle_message(bot: Client, message: Message):  # noqa
    chat_id = message.chat.id
    msg = message.text
    if msg:
        chat_acc = chatId_account.get(chat_id, None)
        if msg.startswith('/start'):
            if chat_acc:
                name, email, _ = search_user(user_id=chat_acc.account_id)
                chat_acc.email = email
                chat_acc.expense = ExpenseStatus()
                bot.send_message(chat_id, f'Hi {name}\nWelcome to splitwise!\n\n'
                                          f'Be aware that you must have added me to your splitwise groups',
                                 reply_markup=InlineKeyboardMarkup(home_keys(InlineKeyboardButton)))
            else:
                bot.send_message(chat_id, f'Welcome to splitwise!\n\nFirst add me to your splitwise groups\n'
                                          f'Then enter your email here to verify',
                                 reply_markup=InlineKeyboardMarkup(about_help_keys(InlineKeyboardButton)))
                chatId_account[chat_id] = Account()
        elif chat_acc:
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
                    chat_acc.expense = ExpenseStatus()
                    bot.send_message(chat_id, ch_mail + 'Check your email and enter Verification code here:\n'
                                                        '(You have 3 chances and 2 minutes)')
                else:
                    bot.send_message(chat_id, 'Something went wrong!\nEnter your email again',
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Back', QueryData.BACK)]])
                                     if chat_acc.status == Status.CHANGE_EMAIL else None)
            elif chat_acc.status == Status.SEND_EMAIL and not chat_acc.verification.is_verify:
                if chat_acc.verification.chance and chat_acc.verification.start_time + timedelta(
                        minutes=2) >= datetime.now():
                    chat_acc.verification.chance -= 1
                    if msg.isdigit() and int(msg) == chat_acc.verification.code:
                        name, _, acc_id = search_user(email=chat_acc.email)
                        add_user(chat_id, acc_id, chat_acc.email)
                        chat_acc.account_id = acc_id
                        chat_acc.verification.is_verify = True
                        bot.send_message(chat_id, f'Hi {name}\nWelcome to splitwise!',
                                         reply_markup=InlineKeyboardMarkup(home_keys(InlineKeyboardButton)))
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
                    bot.send_message(chat_id, text='Set Details of expense',
                                     reply_markup=InlineKeyboardMarkup(expense_details(InlineKeyboardButton, chat_acc)))
                    chat_acc.status = None
                elif chat_acc.status == QueryData.AMOUNT:
                    if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                        chat_acc.expense.amount = str(round(float(msg), 2))
                        if not chat_acc.expense.paid_shares:
                            chat_acc.expense.paid_shares.update({str(chat_acc.account_id): chat_acc.expense.amount})
                        bot.send_message(chat_id, text='Set Paid shares',
                                         reply_markup=InlineKeyboardMarkup(
                                             get_members_paid(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                                              chat_acc.expense.paid_shares) + [
                                                 [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                        chat_acc.status = None
                    else:
                        bot.send_message(chat_id, 'invalid number\nEnter amount again:')
                elif chat_acc.status.startswith(DynamicQueryData.PAID):
                    if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                        u_id = chat_acc.status[3:]
                        chat_acc.expense.paid_shares[u_id] = str(round(float(msg), 2))
                        bot.send_message(chat_id, text='Set Paid shares',
                                         reply_markup=InlineKeyboardMarkup(
                                             get_members_paid(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                                              chat_acc.expense.paid_shares) + [
                                                 [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                        chat_acc.status = None
                elif chat_acc.status.startswith(DynamicQueryData.EXACT_AMOUNT):
                    if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                        u_id = chat_acc.status[3:]
                        chat_acc.expense.owed_shares[u_id] = str(round(float(msg), 2))
                        owed_shares = dict()
                        aliases = {alias: cost for _, alias, cost in select_alias(chat_acc.expense.selected_group_id)}
                        for user_id in chat_acc.expense.owed_shares:
                            owed = chat_acc.expense.owed_shares.get(user_id)
                            if type(owed) == dict:
                                owed_shares[user_id] = 0
                                for alias in owed:
                                    owed_shares[user_id] += float(owed[alias]) * aliases.get(alias, 0)
                                owed_shares[user_id] = str(round(owed_shares[user_id], 2))
                            elif type(owed) == str:
                                owed_shares[user_id] = owed
                        bot.send_message(chat_id, text='Select users and enter amounts:',
                                         reply_markup=InlineKeyboardMarkup(
                                             get_members_exact_amount(chat_acc.expense.selected_group_id,
                                                                      InlineKeyboardButton, owed_shares) + [
                                                 [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                        chat_acc.status = None
                    else:
                        bot.send_message(chat_id, 'invalid number\nEnter amount again:')
                elif chat_acc.status.startswith(QueryData.ADD_ALIAS):
                    if not chat_acc.new_alias.new_name:
                        chat_acc.new_alias = Alias(msg)
                        chat_acc.new_alias.new_name = True
                        bot.send_message(chat_id, text='Enter cost of alias:')
                    else:
                        if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                            chat_acc.new_alias.cost = round(float(msg), 2)
                            add_alias(chat_acc.expense.selected_group_id, chat_acc.new_alias.name,
                                      chat_acc.new_alias.cost)
                            chat_acc.new_alias.new_name = False
                            u_id = chat_acc.status[3:]
                            u_name = get_user_name(int(u_id))
                            bot.send_message(chat_id, text=f'Enter amount or Click from aliases for {u_name}:',
                                             reply_markup=InlineKeyboardMarkup(
                                                 get_aliases(InlineKeyboardButton, chat_acc.expense.selected_group_id,
                                                             u_id, chat_acc.expense.owed_shares.get(u_id))))
                            chat_acc.status = None
                        else:
                            bot.send_message(chat_id, 'invalid number\nEnter amount again:')
                elif chat_acc.status.startswith(QueryData.EDIT_ALIAS):
                    if not chat_acc.new_alias.new_name:
                        chat_acc.new_alias.new_name = msg
                        bot.send_message(chat_id, text=f'Enter cost for {msg}:')
                    else:
                        if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                            chat_acc.new_alias.cost = round(float(msg), 2)
                            update_alias(chat_acc.expense.selected_group_id, chat_acc.new_alias.name,
                                         chat_acc.new_alias.new_name, chat_acc.new_alias.cost)
                            for user_id in chat_acc.expense.owed_shares:
                                owed = chat_acc.expense.owed_shares.get(user_id)
                                if type(owed) == dict and chat_acc.new_alias.name in owed:
                                    chat_acc.expense.owed_shares[user_id][chat_acc.new_alias.new_name] = owed[
                                        chat_acc.new_alias.name]
                            chat_acc.new_alias.new_name = ''
                            u_id = chat_acc.status[3:]
                            u_name = get_user_name(int(u_id))
                            bot.send_message(chat_id, text=f'Enter amount or Click from aliases for {u_name}:',
                                             reply_markup=InlineKeyboardMarkup(
                                                 get_aliases(InlineKeyboardButton, chat_acc.expense.selected_group_id,
                                                             u_id, chat_acc.expense.owed_shares.get(u_id))))
                            chat_acc.status = None
                        else:
                            bot.send_message(chat_id, 'invalid number\nEnter amount again:')
                elif chat_acc.status.startswith(DynamicQueryData.ALIAS) and chat_acc.status.endswith(
                        DynamicQueryData.ENTER_AMOUNT):
                    if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                        u_id, alias = chat_acc.status[3:chat_acc.status.find('_')], chat_acc.status[
                                                                                    chat_acc.status.find('_') + 1:-3]
                        if type(chat_acc.expense.owed_shares.get(u_id)) != dict:
                            chat_acc.expense.owed_shares[u_id] = dict()
                        chat_acc.expense.owed_shares[u_id][alias] = str(round(float(msg), 2))
                        owed_shares = dict()
                        aliases = {alias: cost for _, alias, cost in select_alias(chat_acc.expense.selected_group_id)}
                        for user_id in chat_acc.expense.owed_shares:
                            owed = chat_acc.expense.owed_shares.get(user_id)
                            if type(owed) == dict:
                                owed_shares[user_id] = 0
                                for alias in owed:
                                    owed_shares[user_id] += float(owed[alias]) * aliases.get(alias, 0)
                                owed_shares[user_id] = str(round(owed_shares[user_id], 2))
                            elif type(owed) == str:
                                owed_shares[user_id] = owed
                        u_name = get_user_name(u_id)
                        bot.send_message(chat_id, text=f'Enter amount or Click from aliases for {u_name}:',
                                         reply_markup=InlineKeyboardMarkup(
                                             get_aliases(InlineKeyboardButton, chat_acc.expense.selected_group_id, u_id,
                                                         chat_acc.expense.owed_shares.get(u_id))))
                        chat_acc.status = None
                elif chat_acc.status.startswith(DynamicQueryData.PERCENTAGE) and chat_acc.status.endswith(
                        DynamicQueryData.ENTER_AMOUNT):
                    if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                        u_id = chat_acc.status[3:-3]
                        chat_acc.expense.owed_shares[u_id] = chat_acc.expense.owed_shares.get(u_id, '0')
                        chat_acc.expense.owed_shares[u_id] = str(round(float(msg), 2)) + ' %'
                        bot.send_message(chat_id, text='Enter amount for users:',
                                         reply_markup=InlineKeyboardMarkup(
                                             get_members_percentage(chat_acc.expense.selected_group_id,
                                                                    InlineKeyboardButton,
                                                                    chat_acc.expense.owed_shares) + [
                                                 [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                        chat_acc.status = None
                    else:
                        bot.send_message(chat_id, 'invalid number\nEnter amount again:')
                elif chat_acc.status.startswith(DynamicQueryData.SHARE) and chat_acc.status.endswith(
                        DynamicQueryData.ENTER_AMOUNT):
                    if msg.count('.') <= 1 and msg.replace('.', '').isdigit():
                        u_id = chat_acc.status[3:-3]
                        chat_acc.expense.owed_shares[u_id] = str(round(float(msg), 2))
                        bot.send_message(chat_id, text='Enter amount for users:',
                                         reply_markup=InlineKeyboardMarkup(
                                             get_members_share(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                                               chat_acc.expense.owed_shares) + [
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
                                  reply_markup=InlineKeyboardMarkup(change_account_keys(InlineKeyboardButton)))
            chat_acc.status = Status.CHANGE_EMAIL
        elif query_data == QueryData.BACK:
            chat_acc.expense = ExpenseStatus()
            bot.edit_message_text(chat_id, message_id=msg_id, text='Choose an option',
                                  reply_markup=InlineKeyboardMarkup(home_keys(InlineKeyboardButton)))
        elif query_data == QueryData.SUBMIT:
            if not chat_acc.expense.description:
                bot.edit_message_text(chat_id, message_id=msg_id, text="You haven't description!",
                                      reply_markup=InlineKeyboardMarkup(
                                          expense_details(InlineKeyboardButton, chat_acc)))
                return
            expense_amount = float(chat_acc.expense.amount)
            if not 0 < expense_amount:
                bot.edit_message_text(chat_id, message_id=msg_id, text="Invalid amount!",
                                      reply_markup=InlineKeyboardMarkup(
                                          expense_details(InlineKeyboardButton, chat_acc)))
                return
            if expense_amount != sum([float(i) for i in list(chat_acc.expense.paid_shares.values())]):
                bot.edit_message_text(chat_id, message_id=msg_id, text="Amount and paid shares doesn't match!",
                                      reply_markup=InlineKeyboardMarkup(
                                          expense_details(InlineKeyboardButton, chat_acc)))
                return
            if chat_acc.expense.split_type == 'EQUALLY':
                if '✅' not in list(chat_acc.expense.owed_shares.values()):
                    bot.edit_message_text(chat_id, message_id=msg_id, text="Your split is wrong!\nNobody to split!",
                                          reply_markup=InlineKeyboardMarkup(
                                              expense_details(InlineKeyboardButton, chat_acc)))
                    return
            elif chat_acc.expense.split_type == 'EXACT AMOUNT':
                owed_shares = dict()
                aliases = {alias: cost for _, alias, cost in select_alias(chat_acc.expense.selected_group_id)}
                for user_id in chat_acc.expense.owed_shares:
                    owed = chat_acc.expense.owed_shares.get(user_id)
                    if type(owed) == dict:
                        owed_shares[user_id] = 0
                        for alias in owed:
                            owed_shares[user_id] += float(owed[alias]) * aliases.get(alias, 0)
                        owed_shares[user_id] = str(round(owed_shares[user_id], 2))
                    elif type(owed) == str:
                        owed_shares[user_id] = owed
                sum_of_owed_shares = round(sum([float(i) for i in list(owed_shares.values())]), 2)
                if expense_amount != sum_of_owed_shares:
                    bot.edit_message_text(chat_id, message_id=msg_id,
                                          text=f"Your split is wrong!\n{expense_amount=} but {sum_of_owed_shares=} !",
                                          reply_markup=InlineKeyboardMarkup(
                                              expense_details(InlineKeyboardButton, chat_acc)))
                    return
            elif chat_acc.expense.split_type == 'PERCENTAGE':
                total_percentages = round(
                    sum([float(i.split()[0]) for i in list(chat_acc.expense.owed_shares.values())]), 2)
                if 100 != total_percentages:
                    bot.edit_message_text(chat_id, message_id=msg_id,
                                          text=f"Your split is wrong!\n{total_percentages=} !",
                                          reply_markup=InlineKeyboardMarkup(
                                              expense_details(InlineKeyboardButton, chat_acc)))
                    return
            elif chat_acc.expense.split_type == 'SHARE':
                if 0 >= sum([float(i) for i in list(chat_acc.expense.owed_shares.values())]):
                    bot.edit_message_text(chat_id, message_id=msg_id, text="Your split is wrong!\nNobody to share!",
                                          reply_markup=InlineKeyboardMarkup(
                                              expense_details(InlineKeyboardButton, chat_acc)))
                    return
            else:
                bot.edit_message_text(chat_id, message_id=msg_id, text="No splitting!",
                                      reply_markup=InlineKeyboardMarkup(
                                          expense_details(InlineKeyboardButton, chat_acc)))
                return
            expense = Expense()
            expense.setDescription(chat_acc.expense.description)
            expense.setCost(chat_acc.expense.amount)
            expense.setCurrencyCode(chat_acc.expense.currency)
            expense.setGroupId(chat_acc.expense.selected_group_id)
            user_expense = dict()
            for u_id in chat_acc.expense.paid_shares:
                user_expense[u_id] = ExpenseUser()
                user_expense[u_id].setId(u_id)
                user_expense[u_id].setPaidShare(chat_acc.expense.paid_shares[u_id])
            if chat_acc.expense.split_type == 'EQUALLY':
                count_users = list(chat_acc.expense.owed_shares.values()).count('✅')
                rem = expense_amount - count_users * round(expense_amount / count_users, 2)
                for u_id in chat_acc.expense.owed_shares:
                    user_expense.setdefault(u_id, ExpenseUser())
                    user_expense[u_id].setId(u_id)
                    user_amount = round(expense_amount / count_users, 2)
                    rem = round(rem, 2)
                    if rem > 0:
                        user_amount += 0.01
                        rem -= 0.01
                    elif rem < 0:
                        user_amount -= 0.01
                        rem += 0.01
                    user_expense[u_id].setOwedShare(str(user_amount))
            elif chat_acc.expense.split_type == 'EXACT AMOUNT':
                owed_shares = dict()
                aliases = {alias: cost for _, alias, cost in select_alias(chat_acc.expense.selected_group_id)}
                for u_id in chat_acc.expense.owed_shares:
                    owed = chat_acc.expense.owed_shares.get(u_id)
                    if type(owed) == dict:
                        owed_shares[u_id] = 0
                        for alias in owed:
                            owed_shares[u_id] += float(owed[alias]) * aliases.get(alias, 0)
                        user_expense.setdefault(u_id, ExpenseUser())
                        user_expense[u_id].setId(u_id)
                        user_expense[u_id].setOwedShare(str(owed_shares[u_id]))
                        chat_acc.expense.owed_shares[u_id] = owed_shares[u_id]
                    elif type(owed) == str:
                        user_expense.setdefault(u_id, ExpenseUser())
                        user_expense[u_id].setId(u_id)
                        user_expense[u_id].setOwedShare(owed)
            elif chat_acc.expense.split_type == 'PERCENTAGE':
                sum_of_owed_shares = 0
                for u_id in chat_acc.expense.owed_shares:
                    sum_of_owed_shares += round(
                        float(chat_acc.expense.owed_shares[u_id].split()[0]) * expense_amount / 100, 2)
                rem = expense_amount - sum_of_owed_shares
                for u_id in chat_acc.expense.owed_shares:
                    user_expense.setdefault(u_id, ExpenseUser())
                    user_expense[u_id].setId(u_id)
                    user_amount = round(float(chat_acc.expense.owed_shares[u_id].split()[0]) * expense_amount / 100, 2)
                    rem = round(rem, 2)
                    if rem > 0:
                        user_amount += 0.01
                        rem -= 0.01
                    elif rem < 0:
                        user_amount -= 0.01
                        rem += 0.01
                    user_expense[u_id].setOwedShare(str(user_amount))
            elif chat_acc.expense.split_type == 'SHARE':
                sum_shares = round(sum([float(i) for i in list(chat_acc.expense.owed_shares.values())]), 2)
                sum_of_owed_shares = 0
                for u_id in chat_acc.expense.owed_shares:
                    sum_of_owed_shares += round(float(chat_acc.expense.owed_shares[u_id]) * expense_amount / sum_shares,
                                                2)
                rem = expense_amount - sum_of_owed_shares
                for u_id in chat_acc.expense.owed_shares:
                    user_expense.setdefault(u_id, ExpenseUser())
                    user_expense[u_id].setId(u_id)
                    user_amount = round(float(chat_acc.expense.owed_shares[u_id]) * expense_amount / sum_shares, 2)
                    rem = round(rem, 2)
                    if rem > 0:
                        user_amount += 0.01
                        rem -= 0.01
                    elif rem < 0:
                        user_amount -= 0.01
                        rem += 0.01
                    user_expense[u_id].setOwedShare(str(user_amount))
            expense.setUsers(list(user_expense.values()))
            obj, errors = sObj.createExpense(expense)
            print('Accept') if obj else print('Fail')
            print(errors.getErrors()) if errors else None
            details = ['Expense submit successfully\n',
                       f'Group: {chat_acc.expense.selected_group_name}',
                       f'Description: {chat_acc.expense.description}',
                       f'Amount: {chat_acc.expense.amount}',
                       f'Currency: {chat_acc.expense.currency}',
                       f'Split by: {chat_acc.expense.split_type}',
                       ]
            details += ['Paid by:',
                        *[f'{get_user_name(u_id)}: {chat_acc.expense.paid_shares[u_id]}' for u_id in
                          chat_acc.expense.paid_shares],
                        'Owed by:',
                        *[f'{get_user_name(u_id)}: {chat_acc.expense.owed_shares[u_id]}' for u_id in
                          chat_acc.expense.owed_shares]
                        ]
            bot.edit_message_text(chat_id, message_id=msg_id, text='\n'.join(details))
            bot.send_message(chat_id, 'Choose an option',
                             reply_markup=InlineKeyboardMarkup(home_keys(InlineKeyboardButton)))
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
        elif query_data.startswith(DynamicQueryData.GROUP):
            g_id = query_data[3:]
            if chat_acc.expense.selected_group_name != get_group_name(g_id):
                chat_acc.expense = ExpenseStatus()
                chat_acc.expense.selected_group_id = int(g_id)
                chat_acc.expense.selected_group_name = get_group_name(g_id)
            bot.edit_message_text(chat_id, message_id=msg_id, text='Set Details of expense',
                                  reply_markup=InlineKeyboardMarkup(expense_details(InlineKeyboardButton, chat_acc)))
        elif query_data == QueryData.DESCRIPTION:
            chat_acc.status = QueryData.DESCRIPTION
            bot.edit_message_text(chat_id, message_id=msg_id, text='Enter Description:')
        elif query_data == QueryData.AMOUNT:
            chat_acc.status = QueryData.AMOUNT
            bot.edit_message_text(chat_id, message_id=msg_id, text='Enter Amount:')
        elif query_data == QueryData.CURRENCY:
            chat_acc.expense.currency = 'IRR' if chat_acc.expense.currency == 'USD' else 'USD'
            bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(
                expense_details(InlineKeyboardButton, chat_acc)))
        elif query_data == QueryData.SPLIT_BY:
            bot.edit_message_text(chat_id, message_id=msg_id, text='Split by:',
                                  reply_markup=InlineKeyboardMarkup(split_by_keys(InlineKeyboardButton)))
        elif chat_acc.expense.selected_group_id:
            if query_data.startswith(DynamicQueryData.PAID):
                chat_acc.status = query_data
                bot.edit_message_text(chat_id, message_id=msg_id, text='Enter paid share Amount:')
            elif query_data == QueryData.EQUALLY:
                if chat_acc.expense.split_type != 'EQUALLY':
                    chat_acc.expense.owed_shares.clear()
                    chat_acc.expense.split_type = 'EQUALLY'
                if not chat_acc.expense.owed_shares:
                    chat_acc.expense.owed_shares.update({str(chat_acc.account_id): '✅'})
                bot.edit_message_text(chat_id, message_id=msg_id, text='Select users:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_members_equally(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                                              chat_acc.expense.owed_shares) + [
                                              [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
            elif query_data == QueryData.EXACT_AMOUNT:
                if chat_acc.expense.split_type != 'EXACT AMOUNT':
                    chat_acc.expense.owed_shares.clear()
                    chat_acc.expense.split_type = 'EXACT AMOUNT'
                if not chat_acc.expense.owed_shares:
                    chat_acc.expense.owed_shares.update({str(chat_acc.account_id): chat_acc.expense.amount})
                owed_shares = dict()
                aliases = {alias: cost for _, alias, cost in select_alias(chat_acc.expense.selected_group_id)}
                for user_id in chat_acc.expense.owed_shares:
                    owed = chat_acc.expense.owed_shares.get(user_id)
                    if type(owed) == dict:
                        owed_shares[user_id] = 0
                        for alias in owed:
                            owed_shares[user_id] += float(owed[alias]) * aliases.get(alias, 0)
                        owed_shares[user_id] = str(round(owed_shares[user_id], 2))
                    elif type(owed) == str:
                        owed_shares[user_id] = owed
                bot.edit_message_text(chat_id, message_id=msg_id, text='Select users then enter amounts:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_members_exact_amount(chat_acc.expense.selected_group_id,
                                                                   InlineKeyboardButton, owed_shares) + [
                                              [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
            elif query_data == QueryData.PERCENTAGE:
                if chat_acc.expense.split_type != 'PERCENTAGE':
                    chat_acc.expense.owed_shares.clear()
                    chat_acc.expense.split_type = 'PERCENTAGE'
                if not chat_acc.expense.owed_shares:
                    chat_acc.expense.owed_shares.update({str(chat_acc.account_id): '100 %'})
                bot.edit_message_text(chat_id, message_id=msg_id, text='Select users and enter values:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_members_percentage(chat_acc.expense.selected_group_id,
                                                                 InlineKeyboardButton, chat_acc.expense.owed_shares) + [
                                              [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
            elif query_data == QueryData.SHARE:
                if chat_acc.expense.split_type != 'SHARE':
                    chat_acc.expense.owed_shares.clear()
                    chat_acc.expense.split_type = 'SHARE'
                if not chat_acc.expense.owed_shares:
                    chat_acc.expense.owed_shares.update({str(chat_acc.account_id): '1'})
                bot.edit_message_text(chat_id, message_id=msg_id, text='Select users and enter values:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_members_share(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                                            chat_acc.expense.owed_shares) + [
                                              [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
            elif query_data == QueryData.CONTINUE:
                bot.edit_message_text(chat_id, message_id=msg_id, text='Set Details of expense',
                                      reply_markup=InlineKeyboardMarkup(
                                          expense_details(InlineKeyboardButton, chat_acc)))
            elif query_data == QueryData.CONTINUE_ALIAS:
                owed_shares = dict()
                aliases = {alias: cost for _, alias, cost in select_alias(chat_acc.expense.selected_group_id)}
                for user_id in chat_acc.expense.owed_shares:
                    owed = chat_acc.expense.owed_shares.get(user_id)
                    if type(owed) == dict:
                        owed_shares[user_id] = 0
                        for alias in owed:
                            owed_shares[user_id] += float(owed[alias]) * aliases.get(alias, 0)
                        owed_shares[user_id] = str(round(owed_shares[user_id], 2))
                    elif type(owed) == str:
                        owed_shares[user_id] = owed
                bot.edit_message_text(chat_id, message_id=msg_id, text='Select users then enter amounts:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_members_exact_amount(chat_acc.expense.selected_group_id,
                                                                   InlineKeyboardButton, owed_shares) + [
                                              [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
            elif query_data.startswith(DynamicQueryData.EQUALLY):
                u_id = query_data[3:]
                if not chat_acc.expense.owed_shares.pop(u_id, None):
                    chat_acc.expense.owed_shares.update({u_id: '✅'})
                bot.edit_message_text(chat_id, message_id=msg_id, text='Select users:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_members_equally(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                                              chat_acc.expense.owed_shares) + [
                                              [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
            elif query_data.startswith(DynamicQueryData.EXACT_AMOUNT):
                chat_acc.status = query_data
                u_id = query_data[3:]
                u_name = get_user_name(int(u_id))
                bot.edit_message_text(chat_id, message_id=msg_id,
                                      text=f'Enter amount or Click from aliases for {u_name}:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_aliases(InlineKeyboardButton, chat_acc.expense.selected_group_id, u_id,
                                                      chat_acc.expense.owed_shares.get(u_id))))
            elif query_data.startswith(QueryData.ADD_ALIAS):
                chat_acc.status = query_data
                bot.edit_message_text(chat_id, message_id=msg_id, text=f'Enter name of alias:')
            elif query_data.startswith(QueryData.EDIT_ALIAS) or query_data.startswith(QueryData.DELETE_ALIAS):
                chat_acc.status = query_data
                bot.edit_message_text(chat_id, message_id=msg_id, text=f'Click from aliases:',
                                      reply_markup=InlineKeyboardMarkup(
                                          get_aliases(InlineKeyboardButton, chat_acc.expense.selected_group_id)))
            elif query_data.startswith(DynamicQueryData.ALIAS):
                if query_data.endswith(DynamicQueryData.EDIT) and chat_acc.status.startswith(QueryData.DELETE_ALIAS):
                    delete_alias(chat_acc.expense.selected_group_id, query_data[3:-3])
                    owed_shares = dict()
                    aliases = {alias: cost for _, alias, cost in select_alias(chat_acc.expense.selected_group_id)}
                    for user_id in chat_acc.expense.owed_shares:
                        owed = chat_acc.expense.owed_shares.get(user_id)
                        if type(owed) == dict:
                            owed_shares[user_id] = 0
                            for alias in owed:
                                owed_shares[user_id] += float(owed[alias]) * aliases.get(alias, 0)
                            owed_shares[user_id] = str(round(owed_shares[user_id], 2))
                        elif type(owed) == str:
                            owed_shares[user_id] = owed
                    bot.edit_message_text(chat_id, message_id=msg_id, text='Alias deleted successfully\n'
                                                                           'Select users and enter amounts:',
                                          reply_markup=InlineKeyboardMarkup(
                                              get_members_exact_amount(chat_acc.expense.selected_group_id,
                                                                       InlineKeyboardButton, owed_shares) + [
                                                  [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                elif query_data.endswith(DynamicQueryData.EDIT) and chat_acc.status.startswith(QueryData.EDIT_ALIAS):
                    _, alias, cost = select_alias(chat_acc.expense.selected_group_id, query_data[3:-3])[0]
                    chat_acc.new_alias = Alias(alias, cost)
                    bot.edit_message_text(chat_id, message_id=msg_id, text=f'Enter new name for alias `{alias}`:')
                elif query_data.endswith(DynamicQueryData.ENTER_AMOUNT):
                    chat_acc.status = query_data
                    alias = query_data[query_data.find('_') + 1:-3]
                    bot.edit_message_text(chat_id, message_id=msg_id, text=f'Enter amount for alias {alias}:')
                elif query_data.endswith(DynamicQueryData.PLUS):
                    u_id, alias = query_data[3:query_data.find('_')], query_data[query_data.find('_') + 1:-3]
                    alias_count = chat_acc.expense.owed_shares.setdefault(u_id, {alias: '0'})
                    if type(alias_count) != dict:
                        alias_count = chat_acc.expense.owed_shares[u_id] = {alias: '0'}
                    alias_count[alias] = str(round(float(alias_count.get(alias, '0')) + 1, 2))
                    bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(
                        get_aliases(InlineKeyboardButton, chat_acc.expense.selected_group_id, u_id,
                                    chat_acc.expense.owed_shares.get(u_id))))
                elif query_data.endswith(DynamicQueryData.MINUS):
                    u_id, alias = query_data[3:query_data.find('_')], query_data[query_data.find('_') + 1:-3]
                    alias_count = chat_acc.expense.owed_shares.setdefault(u_id, {alias: '0'})
                    if type(alias_count) != dict:
                        alias_count = chat_acc.expense.owed_shares[u_id] = {alias: '0'}
                    amount = round(float(alias_count.get(alias, '0')) - 1, 2)
                    alias_count[alias] = str(amount if amount >= 0 else 0)
                    bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(
                        get_aliases(InlineKeyboardButton, chat_acc.expense.selected_group_id, u_id,
                                    chat_acc.expense.owed_shares.get(u_id))))
            elif query_data.startswith(DynamicQueryData.PERCENTAGE):
                if query_data.endswith(DynamicQueryData.PLUS):
                    u_id = query_data[3:-3]
                    amount = float(chat_acc.expense.owed_shares.setdefault(u_id, '0 %').split()[0])
                    chat_acc.expense.owed_shares[u_id] = (str(
                        round(amount + 10, 2)) if amount + 10 <= 100 else '100') + ' %'
                    bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(
                        get_members_percentage(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                               chat_acc.expense.owed_shares) + [
                            [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                elif query_data.endswith(DynamicQueryData.MINUS):
                    u_id = query_data[3:-3]
                    amount = float(chat_acc.expense.owed_shares.setdefault(u_id, '0 %').split()[0])
                    chat_acc.expense.owed_shares[u_id] = (str(
                        round(amount - 10, 2)) if amount - 10 >= 0 else '0') + ' %'
                    bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(
                        get_members_percentage(chat_acc.expense.selected_group_id,
                                               InlineKeyboardButton, chat_acc.expense.owed_shares) + [
                            [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                else:
                    chat_acc.status = query_data
                    u_name = get_user_name(int(query_data[3:-3]))
                    bot.edit_message_text(chat_id, message_id=msg_id, text=f'Enter percent for {u_name}:')
            elif query_data.startswith(DynamicQueryData.SHARE):
                if query_data.endswith(DynamicQueryData.PLUS):
                    u_id = query_data[3:-3]
                    amount = float(chat_acc.expense.owed_shares.setdefault(u_id, '0').split()[0])
                    chat_acc.expense.owed_shares[u_id] = str(round(amount + 1, 2))
                    bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(
                        get_members_share(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                          chat_acc.expense.owed_shares) + [
                            [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                elif query_data.endswith(DynamicQueryData.MINUS):
                    u_id = query_data[3:-3]
                    amount = float(chat_acc.expense.owed_shares.setdefault(u_id, '0').split()[0])
                    if 0 < amount:
                        chat_acc.expense.owed_shares[u_id] = str(round(amount - 1, 2)) if amount - 1 >= 0 else '0'
                        bot.edit_message_reply_markup(chat_id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(
                            get_members_share(chat_acc.expense.selected_group_id, InlineKeyboardButton,
                                              chat_acc.expense.owed_shares) + [
                                [InlineKeyboardButton('Continue', QueryData.CONTINUE)]]))
                else:
                    chat_acc.status = query_data
                    u_name = get_user_name(int(query_data[3:-3]))
                    bot.edit_message_text(chat_id, message_id=msg_id, text=f'Enter share value for {u_name}:')
    else:
        bot.send_message(chat_id, "You aren't verify yet\n\nFirst add me to your splitwise groups\n"
                                  "Then enter your email here to verify")
        chat_acc.status = Status.START


for rec in select_user():
    chatId_account[rec[0]] = Account(rec[1], rec[2])
    chatId_account[rec[0]].verification.is_verify = True

client.run()
