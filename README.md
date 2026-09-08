# FlatSplit

Self-hosted expense splitting for a shared flat. Runs on one machine in the
flat; everyone uses it from their phone over the local WiFi. No internet
required once it is running.

> Phase 1 of 9 is complete: scaffold, auth, mobile shell, offline assets, PWA.
> Expenses, splitting, balances and settlements land in later phases.
> Full setup, cron and backup docs arrive with phase 9.

## Run it

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # Linux/macOS

cp .env.example .env          # then edit SECRET_KEY
python manage.py migrate
python manage.py make_icons
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

## Connecting from a phone

Find the host's LAN address:

```bash
python -c "from config.lan import primary_lan_ip; print(primary_lan_ip())"
```

Open `http://<that-address>:8000` on any phone on the same WiFi.
`ALLOWED_HOSTS` is built from `.env` plus every address the host actually
answers to, so LAN IPs work without editing settings.

## Adding flatmates

Log in as an admin, go to **Flat → Add**, and copy the generated link to the
new flatmate. The link lets them set their own password and works exactly
once — there is no email backend, by design.

## Known limitation: service worker over plain HTTP

Chrome only registers service workers on secure origins, and a LAN IP over
`http://` is not one. The app installs and runs fine; only offline caching is
affected. To enable it, add your host to
`chrome://flags/#unsafely-treat-insecure-origin-as-secure` on each phone.
Verify on a real device before relying on offline mode.
