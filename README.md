# nip05er

High five users by adding them to `nostr.json` which is used to validate their nip05 address if it matches `user@your.domain`. The term "nip05er" is an abbreviation of "nip05 user."

* This works withou any necessary web-interface or separate database. The user is never required to fill out a separate form. All they do is set up their nip-05 the way they want to, in the app of their choice. The script will record which users registered a name and ensure the user keeps that name. All of the concerns about the UX remain in the nostr client and there is no additional fees for shorter names. It's a first come first serve basis.

* The script operates on an nostr.json file in-place, and maintains all of your manual modifications. However, you should make regular backups and periodically review the resulting nostr.json, just in-case there are any unforseen issues with this lightly tested script that you got for free. 🙃

## reports

Helper script to show all NIP-1984 reports on local users by local users.

## installation

```bash
pip install --upgrade pip
pip install bleetube-nip05er
```

## configure secrets

We automatically read database connection parameters from an environment file named `.env` by default:

```bash
DB_HOST=/var/run/postgresql
DB_PORT=5432
DB_NAME=nostream
DB_USER=nostream
DB_PASSWORD='hunter2'
RELAY_DOMAIN=bitcoiner.social
NIP05ER_JSON=/var/www/html/.well-known/nostr.json
NIP05ER_DATA=/var/cache/nip05er
NIP05ER_LOG_PATH=/var/log/nip05er.log
```

The last couple variables are unique to this script. The rest overlap with what you would already have configured in a docker-compose environment file.

## running

```bash
nip05er update
```

## troubleshooting

You can have the script dump all the environment variables:

```bash
nip05er update --showvars
```

## Development

Clone the repo and install dependencies into a local virtual environment:

```bash
git clone git@github.com/bleetube/nip05er
cd nip05er
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install --editable .
nip05er update
reports show
```

todo:

- Remove names if they no longer appear in the user's profile.
- We should also check external relays because the client isn't guaranteed to have broadcast the profile to our local relay.
- When checking external relays, we should use only the most recent event
