class Account:
    def __init__(self, account_id=None, email=''):
        self.status = Status.START
        self.account_id = account_id
        self.email = email
        self.verification = Verification()
        self.expense = ExpenseStatus()
        self.new_alias = Alias()


class Alias:
    def __init__(self, name='', cost=0):
        self.name = name
        self.cost = cost
        self.new_name = ''


class ExpenseStatus:
    def __init__(self):
        self.expense_id = None
        self.selected_group_id = 0
        self.selected_group_name = ''
        self.amount = '0'
        self.description = ''
        self.currency = 'USD'
        self.split_type = ''
        self.paid_shares = dict()  # user_id: PaidShare
        self.owed_shares = dict()  # user_id: OwedShare


class Verification:
    def __init__(self):
        self.is_verify = False
        self.start_time = None
        self.code = None
        self.chance = 3


class Status:
    START = 0
    SEND_EMAIL = 1
    CHANGE_EMAIL = 2


class QueryData:
    BACK = 's00'
    ADD_EXPENSE = 's01'
    BALANCE = 's02'
    CHANGE_ACCOUNT = 's03'
    ABOUT = 's04'
    HELP = 's05'
    EQUALLY = 's06'
    EXACT_AMOUNT = 's07'
    PERCENTAGE = 's08'
    SHARE = 's09'
    DESCRIPTION = 's10'
    AMOUNT = 's11'
    CURRENCY = 's12'
    SPLIT_BY = 's13'
    CONTINUE = 's14'
    ADD_ALIAS = 's15'
    DELETE_ALIAS = 's16'
    EDIT_ALIAS = 's17'
    CONTINUE_ALIAS = 's18'
    SUBMIT = 's19'


class DynamicQueryData:
    GROUP = 'daa'
    PAID = 'dab'
    EQUALLY = 'dac'
    EXACT_AMOUNT = 'dad'
    PERCENTAGE = 'dae'
    SHARE = 'daf'
    ENTER_AMOUNT = 'dag'
    PLUS = 'dah'
    MINUS = 'dai'
    ALIAS = 'daj'
    EDIT = 'dak'
    EDIT_EXPENSE = 'dal'
    DELETE_EXPENSE = 'dam'
    OPTIONS = 'dan'
