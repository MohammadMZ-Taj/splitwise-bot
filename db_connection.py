from psycopg import connect, errors, sql

from settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS


def create_database():
    conn = connect(user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    cur = conn.cursor()
    conn.autocommit = True
    try:
        create_cmd = sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DB_NAME))
        cur.execute(create_cmd)
        conn.close()
    except errors.DuplicateDatabase:
        conn.rollback()
    conn = connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    cur = conn.cursor()
    try:
        cur.execute('''CREATE TABLE SPLITWISE_USER
              (TELEGRAM_ID BIGINT NOT NULL,
              SPLITWISE_ID BIGINT NOT NULL,
              EMAIL VARCHAR NOT NULL,
              PRIMARY KEY (TELEGRAM_ID)
              );''')
        conn.commit()
    except errors.DuplicateTable:
        conn.rollback()
    try:
        cur.execute('''CREATE TABLE GROUP_ALIASES
              (GROUP_ID BIGINT NOT NULL,
              ALIAS VARCHAR NOT NULL,
              COST BIGINT NOT NULL,
              PRIMARY KEY (GROUP_ID, ALIAS)
              );''')
        conn.commit()
    except errors.DuplicateTable:
        conn.rollback()
    return conn, cur


Conn, Cur = create_database()


def add_user(telegram_id, splitwise_id, email):
    try:
        Cur.execute("INSERT INTO SPLITWISE_USER VALUES (%s, %s, %s)", [telegram_id, splitwise_id, email])
    except errors.UniqueViolation:
        Conn.rollback()
    Conn.commit()


def select_user(telegram_id=None):
    if telegram_id:
        Cur.execute("SELECT * FROM SPLITWISE_USER WHERE TELEGRAM_ID=(%s)", [telegram_id])
    else:
        Cur.execute("SELECT * FROM SPLITWISE_USER")
    return Cur.fetchall()


def delete_user(telegram_id):
    Cur.execute("DELETE FROM SPLITWISE_USER WHERE TELEGRAM_ID=(%s)", [telegram_id])
    Conn.commit()


def update_user(telegram_id, splitwise_id, email):
    Cur.execute("UPDATE SPLITWISE_USER SET SPLITWISE_ID=(%s), EMAIL=(%s) WHERE TELEGRAM_ID=(%s)",
                [splitwise_id, email, telegram_id])
    Conn.commit()


def add_alias(group_id, alias, cost):
    try:
        Cur.execute("INSERT INTO GROUP_ALIASES VALUES (%s, %s, %s)", [group_id, alias, cost])
    except errors.UniqueViolation:
        Conn.rollback()
    Conn.commit()


def select_alias(group_id=None, alias=None):
    if group_id and alias:
        Cur.execute("SELECT * FROM GROUP_ALIASES WHERE GROUP_ID=(%s) AND ALIAS=(%s)", [group_id, alias])
    elif group_id:
        Cur.execute("SELECT * FROM GROUP_ALIASES WHERE GROUP_ID=(%s)", [group_id])
    else:
        Cur.execute("SELECT * FROM GROUP_ALIASES")
    return Cur.fetchall()


def delete_alias(group_id, alias):
    Cur.execute("DELETE FROM GROUP_ALIASES WHERE GROUP_ID=(%s) AND ALIAS=(%s)", [group_id, alias])
    Conn.commit()


def update_alias(group_id, old_alias, new_alias=None, cost=None):
    rec = select_alias(group_id, old_alias)[0]
    new_alias = new_alias or rec[1]
    cost = cost or rec[2]
    Cur.execute("UPDATE GROUP_ALIASES SET ALIAS=(%s), COST=(%s) WHERE GROUP_ID=(%s) AND ALIAS=(%s)",
                [new_alias, cost, group_id, old_alias])
    Conn.commit()
