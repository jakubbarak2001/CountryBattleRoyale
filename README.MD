# Country Battle Royale

Small Flask app that compares two countries using data from the REST Countries API.

Current scoring:
- larger population = 1 point
- larger area = 1 point

The app can also generate two random countries and let the user guess which one will win.

## Tech

- Python
- Flask
- Jinja
- REST Countries API
- HTML/CSS

## Setup

Create `.env`:

```env
MY_SECRET_KEY=your_api_key_here

Install dependencies:

pip install -r requirements.txt

Run:

python app.py

Then open:

http://127.0.0.1:5000
Status

Still a small learning project and work in progress.