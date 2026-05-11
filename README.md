# wastemap-ai

A MVP of Wastemap AI, a project for UCLA Anderson MBA class Management 248, Technology and Society.

## Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata fixtures/initial_data.json
python manage.py changepassword admin
python manage.py runserver
```

Then open <http://localhost:8000>.

## Management Commands

### Project-specific

#### `seed_metros`

Seeds metropolitan-area `Section`s, neighborhood `Subsection`s, and random `WasteItem` records spread across the last 90 days. Idempotent on geography (won't duplicate sections/subsections); appends new `WasteItem`s each run.

```bash
python manage.py seed_metros
python manage.py seed_metros --items-per-subsection 60 --days 120
python manage.py seed_metros --clear        # wipe existing WasteItems first
```

Flags:

- `--items-per-subsection N` (default `40`) — random items per neighborhood
- `--days N` (default `90`) — spread timestamps over the last N days
- `--clear` — delete existing `WasteItem` rows before seeding

Metros seeded: West LA (from the fixture) plus New York City, Chicago, San Francisco, Seattle, Boston, Miami, Houston, and Denver — each with five neighborhood subsections.

### Standard Django commands you'll use

```bash
python manage.py migrate                    # apply migrations
python manage.py loaddata fixtures/initial_data.json   # load West LA + admin user
python manage.py changepassword <username>  # set/reset a password
python manage.py createsuperuser            # create a new superuser
python manage.py runserver                  # start the dev server (Daphne via Channels)
python manage.py shell                      # interactive Django shell
python manage.py check                      # system check
```

## Notes

- The `admin` user is created by the fixture with an unusable password (`!notset`). **You must run `python manage.py changepassword admin` before logging in.**
- Copy `.env.example` to `.env` and set `SECRET_KEY` before deploying to production.
- The `CHANNEL_LAYERS` setting uses `InMemoryChannelLayer` (dev only). Switch to `RedisChannelLayer` for production.
- The live monitoring page requires camera access via `navigator.mediaDevices.getUserMedia`, which **only works over HTTPS or `http://localhost`**. LAN IPs (e.g. `http://192.168.x.x:8000`) will fail with "Your browser does not support camera access".
- On the first inference, the YOLOv8 waste classifier (`kendrickfff/waste-classification-yolov8-ken`, ~51 MB) is downloaded from HuggingFace and cached locally. Subsequent inferences reuse the cached weights.
