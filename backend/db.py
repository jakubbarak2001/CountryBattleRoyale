import os

import psycopg
from psycopg.rows import dict_row
from argon2 import PasswordHasher

password_hasher = PasswordHasher()

