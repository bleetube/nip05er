# nip05er

High five users by adding them to `nostr.json` which is used to validate their nip05 address if it matches `user@your.domain`.

## installation

```bash
pip install --upgrade pip
pip install bleetube-nip05er
```

## configure secrets

You need to source the environment variables for connecting to the nostream database. For example, you can create an `.env` environment file and then do `source .env`:

```bash
export DB_HOST=/var/run/postgresql
export DB_PORT=5432
export DB_NAME=nostream
export DB_USER=nostream
export DB_PASSWORD='hunter2'
export RELAY_DOMAIN=bitcoiner.social
export RELAY_ADMIN=blee
```

## running

Use `--help` to see the console documentation. Otherwise you can just call the entry point and it should write `nostr.json` as well as print the results:

```bash
nip05er
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
source .env
nip05er --help
```

In case you're on Arch like myself, you'll need to `pacman -S python-psycopg2` to avoid errors about building dependencies from source.
