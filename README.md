# FlatSplit

Self-hosted expense splitting for a shared flat. It runs on one machine in the
flat; everyone uses it from their phone over the local WiFi. No internet needed
once it is running, and nothing leaves the house.

- Rent, electricity, WiFi, maintenance, groceries, gas, maid, one-offs
- Four split types: equally, exact amounts, percentages, shares
- **Away days** — food, gas and the maid are split by who was actually here
- **Move-in / move-out** — rent is prorated by days of tenancy
- Settlements that only count once the receiver confirms them
- UPI deep links and QR codes, generated offline
- Recurring bills, with variable ones arriving as drafts to fill in
- Audit log, month closing, monthly summary, CSV export
- Installs to the home screen as a PWA

---

## Setup

Needs Python 3.11 or newer.

```bash
git clone <this repo> flatsplit && cd flatsplit

python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows

pip install -r requirements.txt

cp .env.example .env               # then edit SECRET_KEY — see below
python manage.py migrate
python manage.py make_icons
python manage.py createsuperuser
```

Generate a real secret key and paste it into `.env`:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

### `.env`

```ini
DEBUG=True
SECRET_KEY=paste-the-generated-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.5
DJANGO_SETTINGS_MODULE=config.settings.dev
```

`ALLOWED_HOSTS` is a starting point, not the whole list. Django has no wildcard
form for `192.168.*`, so instead of guessing your subnet the app detects the
addresses this machine actually answers to at startup and adds them. Listing
your LAN IP here is belt and braces.

### Try it with demo data

```bash
python manage.py seed_demo
```

Four flatmates, a month of realistic bills, two trips away, a mid-month
move-in, and settlements in every state. Log in as `anuj`, `priya`, `rohit` or
`meera`, password `flatsplit`. **Change those before anyone real uses it.**

When you are done looking around, throw it all away:

```bash
python manage.py seed_demo --clear     # remove the demo data, keep the app
python manage.py seed_demo --reset     # remove it and seed a fresh month
```

`--clear` deletes every demo flatmate, expense, settlement, away period,
recurring template and audit entry. It keeps the eight categories, which come
from a migration rather than the demo. It also removes the demo superuser, so
run `createsuperuser` afterwards before you try to log in.

---

## Running it

**While you are working on it:**

```bash
python manage.py runserver 0.0.0.0:8000
```

**For real:**

```bash
./run.sh
```

That applies migrations, collects static files, prints the LAN address, and
serves through Gunicorn on `0.0.0.0:8000`. On Windows it falls back to
Waitress, since Gunicorn has no Windows support.

### Keeping it running

On a Linux host, a systemd unit is the least fuss:

```ini
# /etc/systemd/system/flatsplit.service
[Unit]
Description=FlatSplit
After=network.target

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/flatsplit
ExecStart=/home/YOUR_USERNAME/flatsplit/run.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now flatsplit
```

---

## Connecting from a phone

Find the host's address:

```bash
python -c "from config.lan import primary_lan_ip; print(primary_lan_ip())"
```

Or the usual way: `ip addr` / `ifconfig` on Linux and macOS, `ipconfig` on
Windows — you want the `192.168.x.x` or `10.x.x.x` one.

Everyone opens **`http://<that-address>:8000`** on the flat WiFi. In Chrome or
Safari, use "Add to Home screen" and it installs like an app.

**Give the host a fixed address.** Most home routers will reserve one against
the machine's MAC address ("DHCP reservation" in the admin page). Without it
the IP can change on reboot and everyone's home-screen icon breaks.

**Check the firewall** if phones cannot connect:

```bash
sudo ufw allow 8000/tcp                                    # Linux
netsh advfirewall firewall add rule name="FlatSplit" ^
  dir=in action=allow protocol=TCP localport=8000          # Windows
```

### Adding flatmates

**Any** flatmate can do this — gatekeeping who joins is friction with no
benefit when everyone already sees all the money. Go to **Flat → Flatmates →
Add**, then hit **Share** to open your phone's own share sheet (WhatsApp
included) or **Copy link**.

The link lets them pick their own password and stops working the moment they
use it. There is no email backend, deliberately — one less thing to configure
on a machine with no internet.

Lost the link? The flatmates list shows **Share link** next to anyone who has
not joined yet, and regenerates it. Changing someone else's tenancy dates or
deactivating them stays admin-only.

### Categories

**Flat → Categories** lists what the flat spends on and lets you add your own.
Instead of two confusing checkboxes, each category has one plain-English rule:

| Rule | Prorated by | Use it for |
|---|---|---|
| Split evenly, always | nothing | one-off buys, shared gifts |
| By days lived here | move-in / move-out | rent, WiFi, maintenance |
| By days actually present | move-in **and** away days | food, gas, the maid |

A category already used by an expense cannot be deleted — rename it instead.

### Light and dark

The button in the top bar cycles **Auto → Light → Dark**. Auto follows your
phone. The choice is saved per device and applied before the page paints, so
there is no flash of the wrong theme.

---

## The two rules worth understanding

These are the parts people argue about, so they are worth stating plainly.

### Away days

Mark the days you were not in the flat under **Away days**. Both dates count:
5th to 8th is **four** days, not two. The rule to remember is *mark every day
you weren't here for dinner*.

Away days only affect categories flagged **prorate by away days** — groceries,
gas, the maid. They deliberately do **not** affect rent, WiFi or maintenance:
your room sits empty while you travel, and it still costs what it costs.

Move-in and move-out dates prorate everything with **prorate by move-in**,
rent included. Nobody is ever charged for days before they moved in.

For an expense covering several days, set a **period** on it. A weekly grocery
shop with a period of the 5th to the 11th is split by who was there over that
week. Without a period, an expense is treated as a single day.

Someone away for a whole period shows as **₹0.00** rather than disappearing, so
it is obvious they were considered and excused rather than forgotten.

### Rounding

Every split is computed in whole paise, never in floating point. Shares are
rounded down, then the leftover paise are handed out one each to whoever was
rounded down hardest — ties go to whoever paid. On an even split every fraction
is identical, so in practice the payer absorbs the odd paise:

```
₹100 ÷ 3  →  ₹33.34 (payer), ₹33.33, ₹33.33
```

Every set of shares adds back up to the expense total exactly. There are
property tests over thousands of random splits asserting precisely that.

---

## Recurring bills

Set templates up under **Recurring**. Fixed bills carry their amount; variable
ones (electricity) generate a **draft** with no amount, which the dashboard
nags about until somebody reads the meter.

Generate a month by hand from that screen, or leave it to cron:

```cron
# Every day at 6am. Running it repeatedly is harmless — nothing duplicates.
0 6 * * * cd /home/YOUR_USERNAME/flatsplit && .venv/bin/python manage.py generate_recurring >> cron.log 2>&1
```

Idempotency is a hard requirement here, not a nicety: generated expenses carry
a link back to their template, and the month is checked before anything is
written. Running it five times leaves exactly one expense, and it will not
overwrite a draft somebody has already filled in.

`--dry-run` reports what it would do without writing.

On Windows, use Task Scheduler with the same command.

---

## Running it on a phone with Termux

An old Android phone makes a good always-on host: it is silent, sips power,
and is already on the flat's WiFi. Install Termux from F-Droid — the Play
Store build is abandoned and will not work.

```bash
pkg update && pkg upgrade
pkg install python git libjpeg-turbo libpng zlib freetype
```

Those four libraries are not optional. Pillow builds against them, and
`pip install Pillow` fails on a bare Termux with a compiler error that does
not obviously say so.

```bash
git clone https://github.com/PRiNCeKUsHW/Split.git flatsplit
cd flatsplit

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
#   paste that into SECRET_KEY in .env

python manage.py migrate
python manage.py make_icons
python manage.py createsuperuser
```

### Starting it

```bash
termux-wake-lock          # or Android suspends the process when the screen sleeps
./run.sh
```

If `./run.sh` reports "no such file or directory", the shebang is the problem:
Termux has no real `/usr/bin/env`. Either run `termux-fix-shebang run.sh
backup.sh` once, or just call it as `bash run.sh`.

`termux-wake-lock` matters more than anything else here. Without it Android
will freeze the server the moment the screen turns off, and the app becomes
unreachable until you unlock the phone. Release it with `termux-wake-unlock`.

There is no systemd on Termux, so the unit file above does not apply. To keep
it running after you close Termux:

```bash
pkg install termux-services
mkdir -p $PREFIX/var/service/flatsplit
cat > $PREFIX/var/service/flatsplit/run <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
exec 2>&1
cd /data/data/com.termux/files/home/flatsplit
exec ./run.sh
EOF
chmod +x $PREFIX/var/service/flatsplit/run
sv-enable flatsplit
```

Then in Android's settings, exclude Termux from battery optimisation. Android
kills background processes aggressively and this is the usual reason a
self-hosted server "randomly stops".

### Finding the phone's address

```bash
python -c "from config.lan import primary_lan_ip; print(primary_lan_ip())"
```

Everyone else on the WiFi opens `http://<that address>:8000`. Reserve the
address on your router against the phone's MAC, or it will change on reboot
and every home-screen icon in the flat will break.

### Recurring bills and backups on Termux

Cron is not installed by default:

```bash
pkg install cronie
crond
crontab -e
```

```cron
0 6 * * * cd ~/flatsplit && .venv/bin/python manage.py generate_recurring >> cron.log 2>&1
30 2 * * * cd ~/flatsplit && ./backup.sh >> backup.log 2>&1
```

To get backups somewhere you can reach from the phone's file manager:

```bash
termux-setup-storage
./backup.sh ~/storage/downloads/flatsplit-backups
```

**Not verified on a device.** These steps follow Termux's documented
behaviour, but this project has only been run on desktop Python. Expect to
adjust the Pillow build and the service paths.

---

## Backups

```bash
./backup.sh                  # writes to ./backups
./backup.sh /mnt/usb/flat    # or wherever
```

Takes a consistent SQLite snapshot (via `.backup`, so it is safe to run while
the app is serving) and tars up `media/`. Keeps the last 30 of each.

Nightly:

```cron
30 2 * * * cd /home/YOUR_USERNAME/flatsplit && ./backup.sh >> backup.log 2>&1
```

**Copy those backups off the machine.** A snapshot on the same disk as the
original is not a backup — it is a second copy of a single point of failure.
The two things that matter are `db.sqlite3` and `media/`; everything else is in
the repo.

---

## Month closing

**Summary → Close month** makes that month's expenses read-only. This is
enforced in the forms and the views, not merely hidden in the UI, so a stale
browser tab cannot post an edit into a closed month. Reopen from the same
screen.

---

## Development

```bash
pytest                       # the whole suite
pytest expenses -q           # just the split engine
pytest -k rounding           # the rounding tests
```

The money logic lives in `services.py` modules and is tested without a
database. `expenses/services/split.py` imports nothing from Django at all.

```
config/       settings split, LAN host detection, URLs
accounts/     custom User, invite links, away periods
expenses/     Category, Expense, ExpenseShare, the split engine
settlements/  Settlement, balances, debt simplification, UPI + QR
recurring/    templates and the generate_recurring command
core/         dashboard, summary, CSV, audit log, month close
```

Design notes and decisions are in `docs/superpowers/specs/`.

---

## Known limitations

**Service workers over plain HTTP.** Chrome only registers service workers on
secure origins, and a LAN IP over `http://` is not one. The app installs and
runs fine; only offline caching is affected. To enable it, add the host to
`chrome://flags/#unsafely-treat-insecure-origin-as-secure` on each phone.
Verify on a real device before relying on offline mode.

**No authentication between the app and the network.** Anyone on your WiFi who
knows the address can reach the login page. That is the intended threat model
for a flat. Do not port-forward this to the internet.

**Debt simplification is greedy, not provably minimal.** Matching the largest
creditor with the largest debtor never exceeds n−1 payments and is instant for
a flat's worth of people. The theoretically minimal set is NP-hard and would
not produce fewer payments at this scale.
