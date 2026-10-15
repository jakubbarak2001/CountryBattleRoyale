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
        return row[0]

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

            rounds_played = row[0]

            return rounds_played


def write_rounds_played(entered_username):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET rounds_played = rounds_played + 1 WHERE username = %s",
                        (entered_username,))


def write_rounds_won(entered_username):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET rounds_won = rounds_won + 1 WHERE username = %s",
                        (entered_username,))


def read_rounds_won(entered_username):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT rounds_won FROM users WHERE username = %s",
                        (entered_username,))

            row = cur.fetchone()

            if row is None:
                return None

            rounds_won = row[0]

            return rounds_won

def write_best_streak(entered_username):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET best_streak = best_streak + 1 WHERE username = %s",
                        (entered_username,))

def read_best_streak(entered_username):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT best_streak FROM users WHERE username = %s",
                        (entered_username,))

            row = cur.fetchone()

            if row is None:
                return None

            best_streak = row[0]

            return best_streak

def complete_round(round_id, *, user_id=None, guest_id=None, is_correct=False, streak=0):
    """Claim a round and save its score in the same database transaction."""
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE rounds SET completed = TRUE "
                "WHERE round_id = %s AND completed = FALSE "
                "AND (user_id = %s OR (user_id IS NULL AND guest_id = %s)) "
                "RETURNING round_id",
                (round_id, user_id, guest_id),
            )
            if cur.fetchone() is None:
                return False

            # A guest can log in during a round. Their guest ID still proves
            # ownership, and the result now counts towards their account.
            if user_id is not None:
                cur.execute(
                    "UPDATE users SET rounds_played = rounds_played + 1, "
                    "rounds_won = rounds_won + %s, "
                    "best_streak = GREATEST(best_streak, %s) WHERE id = %s",
                    (int(is_correct), streak, user_id),
                )
                if cur.rowcount != 1:
                    raise ValueError("The round's player account no longer exists")

            return True


def create_round(user_id=None, guest_id=None):
    if (user_id is None) == (guest_id is None):
        raise ValueError("A round needs exactly one owner")

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO rounds (user_id, guest_id) VALUES (%s, %s) RETURNING round_id",
                        (user_id, guest_id,))

            return cur.fetchone()[0]
