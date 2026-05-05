# wastemap-ai
A MVP of Wastemap AI, a project for UCLA Anderson MBA class Management 248, Technology and Society

## Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata fixtures/initial_data.json
# Set the admin password (fixture creates user with unusable password):
python manage.py changepassword admin
python manage.py runserver
```

## Notes

- The `admin` user is created by the fixture with an unusable password (`!notset`).
  **You must run `python manage.py changepassword admin` before logging in.**
- Copy `.env.example` to `.env` and set `SECRET_KEY` before deploying to production.
- The `CHANNEL_LAYERS` setting uses `InMemoryChannelLayer` (dev only). Switch to `RedisChannelLayer` for production.

