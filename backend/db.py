import os

import psycopg
from argon2 import PasswordHasher

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