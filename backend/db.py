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
        return password_hasher.verify(row[1], password)
    except VerifyMismatchError:
        return False