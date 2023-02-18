# this works but was used for studying async and websockets. its deprecated, use nip05er.py instead
import asyncio, json, re, secrets
import click, psycopg2, websockets
from pprint import pprint
from binascii import hexlify
from time import sleep, time
from os import environ, getcwd, makedirs, path
from sys import exit
#from asyncio import get_event_loop
#from websockets import connect, exceptions

data_dir = environ.get('DATA_DIR', getcwd())
relay_domain = environ.get('RELAY_DOMAIN', 'bitcoiner.social')
relay_admin = environ.get('RELAY_ADMIN', 'blee')
#cache_age_sec = int(environ.get('CACHE_AGE_SECONDS', 86400))
cache_age_sec = int(environ.get('CACHE_AGE_SECONDS', 1))
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

@click.command()
def save_users() -> None:
    '''Save paid user pubkeys to a file.'''
    users = get_users()
    with open(f"{data_dir}/users.json", 'w') as file:
        file.write(json.dumps(users))

def load_users() -> list:
    '''Load paid user pubkeys from a file.'''
    with open(f"{data_dir}/users.json", 'r') as file:
        users = json.load(file)
    return users

async def ws_nip05er_search() -> dict:
    users = get_users()
#   users = load_users()
    if not path.exists(f"{data_dir}/users"):
        makedirs(f"{data_dir}/users")
    async with websockets.connect(f"wss://{relay_domain}") as websocket:
        subscription_id = secrets.token_urlsafe()
        close_subscription = json.dumps([ "CLOSE", subscription_id ])
        local_nip05_users = {}

        for user in users:
            event = None
            user_cache = f"{data_dir}/users/{user['pubkey']}.json"
            # Check local cache before querying the relay
            if path.exists(user_cache) and time() - path.getmtime(user_cache) < cache_age_sec:
                with open(user_cache, 'r') as file:
                    event = json.load(file)
                    print(f"Loaded {event[0]} for {user['pubkey']}.", end=' ')
            else:
                nostr_request = json.dumps([
                    "REQ",
                    subscription_id,
                    {
                        "authors": [user['pubkey']],
                        "limit":1,
                        "kinds":[0]
                    }
                ])
                max_retries = 10
                while max_retries > 0:
                    max_retries -= 1
                    try:
                        await websocket.send(nostr_request)
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        event = json.loads(response)
                        with open(user_cache, 'w') as file:
                            print(f"Relay returned an {event[0]}", end=' ')
                            file.write(json.dumps(event))
                        await asyncio.sleep(0.25)
                        break
                    except asyncio.exceptions.TimeoutError:
                        print('Timed out while waiting for a response, trying again..')
                    except Exception as e:
                        print(e)
                        print(f"Socket died, returning {len(local_nip05_users)} NIP05s.")
                        return local_nip05_users
            if event[0] == "EVENT":
                pubkey = event[2].get("pubkey")
#               if pubkey and pubkey != user['pubkey']:
#                   print(f"Consistency error: Pubkey {pubkey}")
#                   break
                profile = json.loads(event[2].get("content"))
                if not profile or not pubkey:
                    print('')
                    continue
                nostr_identifier = profile.get("nip05")
                if not nostr_identifier:
                    print('')
                    continue

                print(nostr_identifier, end=' ')
                if is_valid_nip05(nostr_identifier) and nostr_identifier.endswith(f"@{relay_domain}"):
                    nip05_user = nostr_identifier.split("@")[0]
                    if nip05_user in nip05_reserved:
                        continue
                    # debugging
#                   if nip05_user == 'testing':
#                       return local_nip05_users
                    local_nip05_users.update({ nip05_user: pubkey })
#           try:
#               profile_pubkey = json.loads(event[2].get("pubkey"))
#               if profile_pubkey != user['pubkey']:
#                   print(f"Consistency error: Pubkey {user['pubkey']}", end=' ')
#           except:
#               pass
            print('')

        await websocket.send(close_subscription)
    return local_nip05_users

async def ws_get_all_nip05() -> dict:
    '''
    Using nostr protocol, search a relay for a list of users with a valid NIP-05 profile.
    This is the slow way to do it, but it was fun to work out.
    '''
#   users = get_users()
    users = load_users()
    if not path.exists(f"{data_dir}/users"):
        makedirs(f"{data_dir}/users")
    async with websockets.connect(f"wss://{relay_domain}") as websocket:
        subscription_id = secrets.token_urlsafe()
        close_subscription = json.dumps([ "CLOSE", subscription_id ])
        local_nip05_users = {}

        for user in users:
            print(f"Checking {user['pubkey']}.")
            user_cache = f"{data_dir}/users/{user['pubkey']}.json"
            # Check local cache before querying the relay
            if path.exists(user_cache) and time() - path.getmtime(user_cache) < cache_age_sec:
                with open(user_cache, 'r') as file:
                    event = json.load(file)
                    print(f"Loaded {event[0]}.", end=' ')
            else:
                nostr_request = json.dumps([
                    "REQ",
                    subscription_id,
                    {
                        "authors": [user['pubkey']],
                        "limit":1,
                        "kinds":[0]
                    }
                ])
                max_retries = 10
                while max_retries > 0:
                    max_retries -= 1
                    try:
                        await websocket.send(nostr_request)
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        event = json.loads(response)
                        if event[0] == "EVENT":
                            nip05er = get_nip05(event)
                            if nip05er:
                                local_nip05_users.update(nip05er)
                        await asyncio.sleep(0.25)
                        break
                    except asyncio.exceptions.TimeoutError:
                        print('Timed out while waiting for a response, trying again..')
                    except Exception as e:
                        print(e)
                        print(f"Socket died, returning {len(local_nip05_users)} NIP05s.")
                        return local_nip05_users

        await websocket.send(close_subscription)
    return local_nip05_users

def get_nip05(event: list):
    profile = json.loads(event[2].get("content", {}))
    nostr_identifier = profile.get("nip05")
    pubkey = profile.get("pubkey")
    if not nostr_identifier or not pubkey:
        return

    if is_valid_nip05(nostr_identifier) and nostr_identifier.endswith(f"@{relay_domain}"):
        nip05_user = nostr_identifier.split("@")[0]
        if nip05_user in nip05_reserved:
            return
        return { nip05_user: pubkey }

async def async_user_search(pubkey: str) -> None:
    '''Searches the local relay for a single user. Mainly for debugging. Never caches.'''
    async with websockets.connect(f"wss://{relay_domain}") as websocket:
        # generate a random hex string
        subscription_id = hexlify(secrets.token_bytes(16)).decode('utf-8')
        close_subscription = json.dumps([ "CLOSE", subscription_id ])

        user = {}
        user['pubkey'] = pubkey
        nostr_request = json.dumps([
            "REQ",
            subscription_id,
            {
                "authors": [user['pubkey']],
                "limit":1,
                "kinds":[0]
            }
        ])
        max_retries = 5
        while max_retries > 0:
            max_retries -= 1
            try:
    #           print(f"Attempting to get profile for {user['pubkey']}.")
    #           print(nostr_req)
                await websocket.send(nostr_request)
    #           print('sent request')
                response = await asyncio.wait_for(websocket.recv(), timeout=2)
    #           print('Got response')
                event = json.loads(response)
    #           print('Loaded response')
                if event[0] == "EVENT":
                    await websocket.send(close_subscription)
                    pprint(event)
                    return event
                elif event[0] == "EOSE":
                    print("No profile found.")
                else:
                    pprint(event)
                break
            except asyncio.exceptions.TimeoutError:
                print('Timed out while waiting for a response, trying again..')
            except Exception as e:
                print(e)
    return

@click.command()
@click.option('--pubkey', prompt='What 32-byte hex pubkey should we search for?', help='32-byte hex public key of the user to find.')
def user_search(pubkey: str) -> None:
    asyncio.run(async_user_search(pubkey))
    return

@click.command()
def create_nip05_json() -> None:
    # https://websockets.readthedocs.io/en/stable/
#   local_nip05_users = asyncio.run(ws_get_all_nip05())
    local_nip05_users = asyncio.run(ws_nip05er_search())

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
cli.add_command(save_users)
