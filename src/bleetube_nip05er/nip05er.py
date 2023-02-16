import json, re, secrets
import click, psycopg2
from pprint import pprint
from binascii import hexlify
from time import sleep, time
from os import environ, getcwd, makedirs, path
from sys import exit
from asyncio import get_event_loop
from websockets import connect

data_dir = environ.get('DATA_DIR', getcwd())
relay_domain = environ.get('RELAY_DOMAIN', 'bitcoiner.social')
relay_admin = environ.get('RELAY_ADMIN', 'blee')
cache_age_sec = int(environ.get('CACHE_AGE_SECONDS', 86400))
nip05_reserved = [ '_', relay_admin ]

@click.group()
def cli():
    pass

def is_valid_nip05(nip05: str) -> bool:
    # same as email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, nip05) is not None

def get_users() -> list:
    '''Get paid user pubkeys.'''
    conn = psycopg2.connect(
        host=environ.get("DB_HOST"),
        database=environ.get("DB_NAME"),
        user=environ.get("DB_USER"),
        password=environ.get("DB_PASSWORD")
    )

    cur = conn.cursor()
    cur.execute("SELECT pubkey FROM users WHERE is_admitted is true")
    user_results = cur.fetchall()
    cur.close()
    conn.close()

    users = []
    for result in user_results:
        user= {}
        user['pubkey'] = hexlify(result[0]).decode('utf-8')
        users.append(user)

    print(f"Found {len(users)} users.")
    return users

async def local_nip05_search() -> dict:
    '''Searches the local relay for users with a configured nip-05 that matches our domain.'''
    users = get_users()
    if not path.exists(f"{data_dir}/users"):
        makedirs(f"{data_dir}/users")
    async with connect(f"wss://{relay_domain}") as websocket:
        # generate a random hex string
        subscription_id = hexlify(secrets.token_bytes(16)).decode('utf-8')
        nostr_close = json.dumps([ "CLOSE", subscription_id ])

        local_nip05_users = {}
        for user in users:
            # Check local cache before querying the relay
            user_cache = f"{data_dir}/users/{user['pubkey']}.json"
            if path.exists(user_cache) and time() - path.getmtime(user_cache) < cache_age_sec:
#               print(f"Using cached data for {user['pubkey']}.")
                with open(user_cache, 'r') as file:
                    event = json.load(file)
            else:
                nostr_req = json.dumps([
                    "REQ",
                    subscription_id,
                    {
                        "authors": [user['pubkey']],
                        "limit":1,
                        "kinds":[0]
                    }
                ])
                try:
                    print(f"Attempting to get profile for {user['pubkey']}.")
                    await websocket.send(nostr_req)
                    response = await websocket.recv()
                    event = json.loads(response)
                    with open(user_cache, 'w') as file:
                        print(f"Writing cached data for {user['pubkey']}.")
                        file.write(json.dumps(event))
                    sleep(1)
                except:
                    print(f"Socket died, returning {len(local_nip05_users)} NIP05s.")
                    return local_nip05_users
            try:
                profile = json.loads(event[2].get("content"))
                nostr_identifier = profile.get("nip05")
                if is_valid_nip05(nostr_identifier) and nostr_identifier.endswith(f"@{relay_domain}"):
                    nip05_user = nostr_identifier.split("@")[0]
                    if nip05_user in nip05_reserved:
                        print(f"NOTICE: Reserved nip-05: {nostr_identifier} with pubkey {user['pubkey']}")
                        continue
# TODO: test for duplicates
#                   if nip05_user in local_nip05_users.keys():
#                       print(f"WARNING: Duplicate NIP05 detected: {nostr_identifier}")
#                       continue
                    local_nip05_users.update({ nip05_user: user['pubkey'] })
            except:
#               print(f"User doesn't have a NIP05: {user['pubkey']}")
                pass

        await websocket.send(nostr_close)
    return local_nip05_users

async def async_user_search(pubkey: str) -> None:
    '''Searches the local relay for a single user. Mainly for debugging. Never caches.'''
    async with connect(f"wss://{relay_domain}") as websocket:
        # generate a random hex string
        subscription_id = hexlify(secrets.token_bytes(16)).decode('utf-8')
        nostr_close = json.dumps([ "CLOSE", subscription_id ])

        user = {}
        user['pubkey'] = pubkey
        nostr_req = json.dumps([
            "REQ",
            subscription_id,
            {
                "authors": [user['pubkey']],
                "limit":1,
                "kinds":[0]
            }
        ])
        try:
            print(f"Attempting to get profile for {user['pubkey']}.")
            print(nostr_req)
            await websocket.send(nostr_req)
            response = await websocket.recv()
            event = json.loads(response)
            pprint(event)
#       except Exception as e:
#           print(e)
#           pass
        except:
            await websocket.send(nostr_close)
            return

    await websocket.send(nostr_close)
    return event

@click.command()
@click.option('--pubkey', prompt='What 32-byte hex pubkey should we search for?', help='32-byte hex public key of the user to find.')
def user_search(pubkey: str) -> None:
    derp = get_event_loop().run_until_complete(async_user_search(pubkey))
    pprint(derp)
    return

@click.command()
def create_nip05_json() -> None:
    local_nip05_users = get_event_loop().run_until_complete(local_nip05_search())

    admin_nip05 = { 
        'blee': '69a0a0910b49a1dbfbc4e4f10df22b5806af5403a228267638f2e908c968228d',
        "_": "111f214dd63c679aa34b102efe774a815594b8271469c6dbe155fc52af872794"
    }
    local_nip05_users.update(admin_nip05)

    nip05_json = {
        "names": local_nip05_users,
        "relays": {
            "69a0a0910b49a1dbfbc4e4f10df22b5806af5403a228267638f2e908c968228d": [
            "wss://bitcoiner.social"
            ],
            "111f214dd63c679aa34b102efe774a815594b8271469c6dbe155fc52af872794": [
            "wss://bitcoiner.social"
            ]
        }
    }

    with open(f"{data_dir}/nostr.json", 'w') as file:
        file.write(json.dumps(nip05_json))
    print(json.dumps(nip05_json))
    return

cli.add_command(create_nip05_json)
cli.add_command(user_search)