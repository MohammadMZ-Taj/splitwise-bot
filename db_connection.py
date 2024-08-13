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
              (USER_ID BIGINT NOT NULL,
              ACCOUNT_ID BIGINT NOT NULL,
              EMAIL VARCHAR NOT NULL,
              PRIMARY KEY (USER_ID)
              );''')
        conn.commit()
    except errors.DuplicateTable:
        conn.rollback()
    return conn, cur


Conn, Cur = create_database()


def add_user(user_id, account_id, email):
    try:
        Cur.execute("INSERT INTO SPLITWISE_USER VALUES (%s, %s, %s)", [user_id, account_id, email])
    except errors.UniqueViolation:
        Conn.rollback()
    Conn.commit()


def select_user(user_id=None):
    if user_id:
        Cur.execute("SELECT * FROM SPLITWISE_USER WHERE USER_ID=(%s)", [user_id])
    else:
        Cur.execute("SELECT * FROM SPLITWISE_USER")
    return Cur.fetchall()


def delete_user(user_id):
    Cur.execute("DELETE FROM SPLITWISE_USER WHERE USER_ID=(%s)", [user_id])
    Conn.commit()


def edit_user(user_id, account_id, email):
    delete_user(user_id)
    add_user(user_id, account_id, email)
