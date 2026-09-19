# Country Battle Royale

A small geography guessing game built with Flask. Two random countries face off: pick the one you think has the higher score, or call a draw, then see how their population and area compare.

![Country Battle Royale showing a Philippines vs. Kuwait matchup, a win streak counter, and Register and Login buttons](docs/images/gameplay.png)

## How to play

1. Compare the two countries while their stats are hidden.
2. Pick a country or choose **Call it a draw**.
3. Reveal the results: larger population earns **1 point**, and larger area earns **1 point**. Equal values award neither country a point for that stat.
4. A correct guess increases your win streak; an incorrect guess resets it. Choose **New matchup** after answering to play another round.

If each country wins one stat, the round is a draw. Clicking **New matchup** before answering keeps the current pair.

## Features and status

- Random country matchups with flags, population, and area.
- A win streak tracked in your browser session, with a flame that changes as the streak grows.
- A responsive layout for desktop and mobile.
- Country data cached locally in `countries.json` and refreshed when it is more than seven days old.
- Register and Login dialogs with password visibility controls. These are **frontend previews**: they do not create accounts or sign users in yet.
- A database helper, `create_user()`, that hashes passwords with Argon2, inserts users into PostgreSQL, and returns their generated ID. It is not connected to the forms yet.

This is a learning project under active development.

## Tech stack

| Area | Tools |
| --- | --- |
| Backend | Python, Flask, Requests |
| Frontend | Jinja2, HTML, CSS, vanilla JavaScript |
| Country data | REST Countries API, local JSON cache |
| User storage | PostgreSQL, Psycopg 3, Argon2 |
| Configuration | python-dotenv |

## Run locally

Use Python 3.12 or newer; development currently uses Python 3.14. Run the following commands from the project root so the app can find its modules and country cache.

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate it with `.venv\Scripts\Activate.ps1` instead.

### 2. Configure the environment

Copy [.env.example](.env.example) to `.env` and replace the placeholders:

```bash
cp .env.example .env
```

```dotenv
MY_SECRET_KEY=your_rest_countries_api_key
FLASK_SECRET_KEY=paste_your_generated_secret_here
DATABASE_URL=postgresql://YOUR_USERNAME:YOUR_PASSWORD@localhost:5432/YOUR_DB
```

| Variable | Purpose |
| --- | --- |
| `MY_SECRET_KEY` | API key for the REST Countries v5 API used in `countries.py`. Needed when the country cache is missing or expired. |
| `FLASK_SECRET_KEY` | Signs Flask's session cookie, which holds the current matchup and streak. |
| `DATABASE_URL` | PostgreSQL connection details for `create_user()`. Optional for playing the game while account features are still being built. |

Generate a Flask secret with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the **output** into `FLASK_SECRET_KEY`; putting the command itself in `.env` will not run it. Keep real credentials in `.env` and exclude that file from Git.

### 3. Start Flask

```bash
python -m flask --app backend.app run --debug
```

Open [localhost:5000](http://127.0.0.1:5000). The first game request downloads country data if no fresh cache exists, so it needs a valid API key and an internet connection. The command above starts the local development server.

## Database development

PostgreSQL is only needed when using [backend/db.py](backend/db.py). The helper expects a `users` table with these columns:

| Column | Value |
| --- | --- |
| `id` | Automatically generated integer ID |
| `username` | Player's username |
| `pass_hash` | Argon2 hash generated from the supplied password |
| `email` | Player's email address |
| `created_at` | Timestamp with a default of `CURRENT_TIMESTAMP` |

Create the database and table separately, and give the role in `DATABASE_URL` permission to use them. The application does not initialize the database automatically. Before calling `create_user()` outside the Flask app, load `.env` with `load_dotenv()` or set the environment variables yourself.

## Project layout

```text
backend/
  app.py               Flask routes and session handling
  db.py                PostgreSQL user creation helper
templates/
  index.html           Game page and account dialogs
static/
  style.css            Page styles and responsive layout
  auth.js              Frontend behavior for Register and Login
  fonts/               Local font assets
  favicon.svg          Site icon
docs/images/
  gameplay.png         README screenshot
countries.py           Country data, caching, and scoring
tests.py               Country comparison test
.env.example           Environment variable template
requirements.txt       Python dependencies
```

## Tests

With the virtual environment active, run:

```bash
python -m unittest tests -v
```

The current test checks the Japan–Germany comparison. It uses the same cache and API as the game, so an expired or missing cache requires API access.

## License

[MIT](LICENSE). The bundled font has its own [license](static/fonts/OFL.txt).
