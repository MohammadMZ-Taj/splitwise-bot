from typing import List

from splitwise import Splitwise, Friend, Group
from splitwise.balance import Balance

from models import DynamicQueryData
from settings import Consumer_Key, Consumer_Secret, API_key


def get_user_name(user_id):
    user: Friend = sObj.getUser(user_id)
    fn = user.getFirstName()
    ln = user.getLastName()
    return fn if fn else '' + ln if ln else ''


def get_group_name(group_id):
    group: Group = sObj.getGroup(group_id)
    return group.getName()


def get_balance(user_id):
    groups: List[Group] = sObj.getGroups()
    res = [f'💰 Balance of **{get_user_name(user_id)}**:']
    for group in groups:
        user: List[Friend] = [j for j in group.getMembers() if j.getId() == user_id]
        if not user:
            continue
        user: Friend = user[0]
        res.append(f'💬 Group: **{group.getName()}**')
        balances: List[Balance] = user.getBalances()
        for k in balances:
            res.append(f'💵 {k.getAmount()} __{k.getCurrencyCode()}__')
        if not balances:
            res.append('🚫 Nothing')
        res.append(5 * '➖')
    return res


def search_user(user_id=None, email=None):
    all_users: List[Friend] = sObj.getFriends()
    for user in all_users:
        if (user_id and user.getId() == user_id) or (email and user.getEmail() == email):
            fn = user.getFirstName()
            ln = user.getLastName()
            return fn if fn else '' + ln if ln else '', user.getEmail(), user.getId()


def get_groups(user_id, func):
    groups: List[Group] = sObj.getGroups()
    group_keys = []
    for group in groups:
        members: List[Friend] = group.getMembers()
        for member in members:
            if user_id == member.getId():
                group_keys.append(func(group.getName(), f'{DynamicQueryData.GROUP}{group.getId()}'))
                break
    return group_keys


def get_members_paid(group_id, func, user_val):
    members: List[Friend] = sObj.getGroup(group_id).getMembers()
    member_keys = []
    for member in members:
        if member.getId() == bot_id:
            continue
        fn = member.getFirstName()
        ln = member.getLastName()
        name = fn if fn else '' + ln if ln else ''
        mem_id = str(member.getId())
        val = user_val.get(mem_id, '0')
        member_keys.append([func(name, DynamicQueryData.PAID + mem_id), func(val, DynamicQueryData.PAID + mem_id)])
    return member_keys


def get_members_equally(group_id, func, user_val):
    members: List[Friend] = sObj.getGroup(group_id).getMembers()
    member_keys = []
    for member in members:
        if member.getId() == bot_id:
            continue
        fn = member.getFirstName()
        ln = member.getLastName()
        name = fn if fn else '' + ln if ln else ''
        mem_id = str(member.getId())
        val = user_val.get(mem_id, '❌')
        member_keys.append(
            [func(name, DynamicQueryData.EQUALLY + mem_id), func(val, DynamicQueryData.EQUALLY + mem_id)])
    return member_keys


def get_members_exact_amount(group_id, func, user_val):
    members: List[Friend] = sObj.getGroup(group_id).getMembers()
    member_keys = []
    for member in members:
        if member.getId() == bot_id:
            continue
        fn = member.getFirstName()
        ln = member.getLastName()
        name = fn if fn else '' + ln if ln else ''
        mem_id = str(member.getId())
        val = user_val.get(mem_id, '0')
        member_keys.append(
            [func(name, DynamicQueryData.EXACT_AMOUNT + mem_id), func(val, DynamicQueryData.EXACT_AMOUNT + mem_id)])
    return member_keys


def get_members_percentage(group_id, func, user_val):
    members: List[Friend] = sObj.getGroup(group_id).getMembers()
    member_keys = []
    for member in members:
        if member.getId() == bot_id:
            continue
        fn = member.getFirstName()
        ln = member.getLastName()
        name = fn if fn else '' + ln if ln else ''
        mem_id = str(member.getId())
        val = user_val.get(mem_id, '0 %')
        member_keys.append([
            func(name, DynamicQueryData.PERCENTAGE + mem_id + DynamicQueryData.ENTER_AMOUNT),
            func(val, DynamicQueryData.PERCENTAGE + mem_id + DynamicQueryData.ENTER_AMOUNT),
            func('⬆️', DynamicQueryData.PERCENTAGE + mem_id + DynamicQueryData.PLUS),
            func('⬇️', DynamicQueryData.PERCENTAGE + mem_id + DynamicQueryData.MINUS)
        ])
    return member_keys


def get_members_share(group_id, func, user_val):
    members: List[Friend] = sObj.getGroup(group_id).getMembers()
    member_keys = []
    for member in members:
        if member.getId() == bot_id:
            continue
        fn = member.getFirstName()
        ln = member.getLastName()
        name = fn if fn else '' + ln if ln else ''
        mem_id = str(member.getId())
        val = user_val.get(mem_id, '0')
        member_keys.append([
            func(name, DynamicQueryData.SHARE + mem_id + DynamicQueryData.ENTER_AMOUNT),
            func(val, DynamicQueryData.SHARE + mem_id + DynamicQueryData.ENTER_AMOUNT),
            func('⬆️', DynamicQueryData.SHARE + mem_id + DynamicQueryData.PLUS),
            func('⬇️', DynamicQueryData.SHARE + mem_id + DynamicQueryData.MINUS)
        ])
    return member_keys


sObj = Splitwise(Consumer_Key, Consumer_Secret, api_key=API_key)
bot_id = sObj.getCurrentUser().getId()

# current = sObj.getCurrentUser()
# groups: List[Group] = sObj.getGroups()
# for i in groups:
#     print(i.getName())
#     members: List[Friend] = i.getMembers()
#     for j in members:
#         fn = j.getFirstName()
#         ln = j.getLastName()
#         print(f"{fn if fn else ''} {ln if ln else ''}:", j.getEmail(), j.getId())
#         balances: List[Balance] = j.getBalances()
#         for k in balances:
#             print(k.getAmount(), k.getCurrencyCode())
#     print('------------------------')
#
# ex = Expense()
# ex.setCost('100000')
# ex.setDescription('test')
# ex.setCurrencyCode('IRR')
#
# user1 = ExpenseUser()
# user2 = ExpenseUser()
#
# user1.setId(current.getId())
# user1.setPaidShare('10000')
# user1.setOwedShare('20000')
#
# user2.setId(j.getId())
# user2.setPaidShare('90000')
# user2.setOwedShare('80000')
# ex.setGroupId(sObj.getGroups()[1].getId())
# ex.setUsers([user1, user2])
# a, b = sObj.createExpense(ex)
# # print(b.getErrors())
# friends: List[Friend] = sObj.getFriends()
# for i in friends:
#     print(f'{i.getFirstName()}:')
#     balances: List[Balance] = i.getBalances()
#     for j in balances:
#         print(j.getAmount(), j.getCurrencyCode())
