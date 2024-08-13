from typing import List

from splitwise import Splitwise, Friend, Group, User

from settings import Consumer_Key, Consumer_Secret, API_key


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
                group_name = group.getName()
                group_keys.append(func(group_name, 'g' + str(group.getId()) + '_' + group_name))
                break
    return group_keys


def get_members_equally(group_id, func, user_val):
    default_val = '❌'
    members: List[Friend] = sObj.getGroup(group_id).getMembers()
    member_keys = []
    for member in members:
        if member.getId() == bot_id:
            continue
        fn = member.getFirstName()
        ln = member.getLastName()
        name = fn if fn else '' + ln if ln else ''
        mem_id = str(member.getId())
        if val := user_val.get(mem_id, None):
            member_keys.append([func(name, 'ue' + mem_id), func(val.paid_share, 'ue' + mem_id)])
        else:
            member_keys.append([func(name, 'ue' + mem_id), func(default_val, 'ue' + mem_id)])
    return member_keys


def get_members_exact_amount(group_id, func, user_val):
    default_val = '0'
    members: List[Friend] = sObj.getGroup(group_id).getMembers()
    member_keys = []
    for member in members:
        if member.getId() == bot_id:
            continue
        fn = member.getFirstName()
        ln = member.getLastName()
        name = fn if fn else '' + ln if ln else ''
        mem_id = str(member.getId())
        if val := user_val.get(mem_id, None):
            member_keys.append(
                [func(name, 'ua' + mem_id + '_' + name), func(val.paid_share, 'ua' + mem_id + '_' + name)])
        else:
            member_keys.append([func(name, 'ua' + mem_id + '_' + name), func(default_val, 'ua' + mem_id + '_' + name)])
    return member_keys


def get_members_percentage(group_id, func, user_val):
    default_val = '0 %'
    members: List[Friend] = sObj.getGroup(group_id).getMembers()
    member_keys = []
    for member in members:
        if member.getId() == bot_id:
            continue
        fn = member.getFirstName()
        ln = member.getLastName()
        name = fn if fn else '' + ln if ln else ''
        mem_id = str(member.getId())
        if val := user_val.get(mem_id, None):
            member_keys.append([
                func(name, 'up' + mem_id + '_' + name + 'e'), func(val.paid_share, 'up' + mem_id + '_' + name + 'e'),
                func('⬆️', 'up' + mem_id + '_' + name + 'p'), func('⬇️', 'up' + mem_id + '_' + name + 'm')
            ])
        else:
            member_keys.append([
                func(name, 'up' + mem_id + '_' + name + 'e'), func(default_val, 'up' + mem_id + '_' + name + 'e'),
                func('⬆️', 'up' + mem_id + '_' + name + 'p'), func('⬇️', 'up' + mem_id + '_' + name + 'm')
            ])
    return member_keys


def get_members_share(group_id, func, user_val):
    default_val = '0'
    members: List[Friend] = sObj.getGroup(group_id).getMembers()
    member_keys = []
    for member in members:
        if member.getId() == bot_id:
            continue
        fn = member.getFirstName()
        ln = member.getLastName()
        name = fn if fn else '' + ln if ln else ''
        mem_id = str(member.getId())
        if val := user_val.get(mem_id, None):
            member_keys.append([
                func(name, 'us' + mem_id + '_' + name + 'e'), func(val.paid_share, 'us' + mem_id + '_' + name + 'e'),
                func('⬆️', 'us' + mem_id + '_' + name + 'p'), func('⬇️', 'us' + mem_id + '_' + name + 'm')
            ])
        else:
            member_keys.append([
                func(name, 'us' + mem_id + '_' + name + 'e'), func(default_val, 'us' + mem_id + '_' + name + 'e'),
                func('⬆️', 'us' + mem_id + '_' + name + 'p'), func('⬇️', 'us' + mem_id + '_' + name + 'm')
            ])
    return member_keys


def get_members(group_id, func, current_user, val, default_val='0'):
    members: List[Friend] = sObj.getGroup(group_id).getMembers()
    member_keys = []
    for member in members:
        if member.getId() == bot_id:
            continue
        fn = member.getFirstName()
        ln = member.getLastName()
        name = fn if fn else '' + ln if ln else ''
        mem_id = str(member.getId())
        if current_user == mem_id:
            member_keys.append([func(name, 'NULL'), func(val, 'u' + mem_id + '_' + name)])
        else:
            member_keys.append([func(name, 'NULL'), func(default_val, 'u' + mem_id + '_' + name)])
    return member_keys


sObj = Splitwise(Consumer_Key, Consumer_Secret, api_key=API_key)
bot_id: User = sObj.getCurrentUser().getId()
# groups: List[Group] = sObj.getGroups()
# print('me:', current.getFirstName())
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


# ex = Expense()
# ex.setCost('100000')
# ex.setDescription('test')
#
# user1 = ExpenseUser()
# user2 = ExpenseUser()
#
# user1.setId(current.getId())
# user1.setPaidShare('100000')
# user1.setOwedShare('20000')
#
# user2.setId(i.getId())
# user2.setPaidShare('0')
# user2.setOwedShare('80000')
#
# ex.setCurrencyCode('IRR')
# ex.setGroupId(sObj.getGroups()[1].getId())
# ex.setUsers([user1, user2])
# sObj.createExpense(ex)
#
# friends: List[Friend] = sObj.getFriends()
# for i in friends:
#     print(f'{i.getFirstName()}:')
#     balances: List[Balance] = i.getBalances()
#     for j in balances:
#         print(j.getAmount(), j.getCurrencyCode())
