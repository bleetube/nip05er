# nip05er

High five users by adding them to `nostr.json` which is used to validate their nip05 address if it matches `user@your.domain`.

Best of all, this works withou any necessary web-interface. The user is never required to fill out a separate form. All they do is set up their nip-05 the way they want to, in the app of their choice. The script will record which users registered a name and ensure the user keeps that name. All of the concerns about the UX remain in the nostr client and there is no additional fees for shorter names. It's a first come first serve basis.

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

```bash
nip05er --help
nip05er user-search --pubkey 69a0a0910b49a1dbfbc4e4f10df22b5806af5403a228267638f2e908c968228d
nip05er create-nip05-json
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

Here's hacky alias to quickly check results before copying them over:

```bash
alias up5="cat $HOME/src/nip05er/nostr.json | jq && echo 'Look good?' && read && cp -v src/nip05er/nostr.json /var/www/static/nostr.json"
```

todo:

- store registered names in a simple database (flat file probably) to prevent duplicate name registrations.
- we should also check external relays because the client isn't guaranteed to have broadcast the profile to our local relay.
