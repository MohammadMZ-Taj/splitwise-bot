class Account:
    def __init__(self, account_id=None, email=''):
        self.status = Status.START
        self.account_id = account_id
        self.email = email
        self.verification = Verification()
        self.expense = ExpenseStatus()


class ExpenseStatus:
    def __init__(self):
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
    BACK = 's0'
    ADD_EXPENSE = 's1'
    HISTORY = 's2'
    CHANGE_ACCOUNT = 's3'
    ABOUT = 's4'
    HELP = 's5'
    EQUALLY = 's6'
    EXACT_AMOUNT = 's7'
    PERCENTAGE = 's8'
    SHARE = 's9'
    DESCRIPTION = 's10'
    AMOUNT = 's11'
    CURRENCY = 's12'
    SPLIT_BY = 's13'
    CONTINUE = 's14'
    SUBMIT = 's15'


class DynamicQueryData:
    GROUP = 'da'
    PAID = 'db'
    EQUALLY = 'dc'
    EXACT_AMOUNT = 'dd'
    PERCENTAGE = 'de'
    SHARE = 'df'
    ENTER_AMOUNT = 'dg'
    PLUS = 'dh'
    MINUS = 'di'
