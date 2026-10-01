import os

import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

password_hasher = PasswordHasher()


def create_user(username, password, email):
    pass_hash = password_hasher.hash(password)

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, pass_hash, email)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (username, pass_hash, email),
            )

            user_id = cur.fetchone()[0]

    write_login_timestamp(user_id)
    return user_id


def login_user(entered_username, password):

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, pass_hash FROM users WHERE username = %s',
                (entered_username,),
            )

            row = cur.fetchone()
            if row is None:
                return False

    try:
        verification = password_hasher.verify(row[1], password)
    except VerifyMismatchError:
        return False

    if verification:
        write_login_timestamp(row[0])
        return True

    else:
        return False


def write_login_timestamp(user_id):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP where id = %s",
                        (user_id,),
                        )

def read_rounds_played(entered_username):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT rounds_played FROM users WHERE username = %s",
                        (entered_username,))

            row = cur.fetchone()

            if row is None:
                return None

            rounds_played =  row[0]

            return rounds_played