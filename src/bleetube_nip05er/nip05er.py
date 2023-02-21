import json, re
import click, psycopg2
from pprint import pprint
#from binascii import hexlify
from time import sleep, time
from os import environ, getcwd

data_dir = environ.get('DATA_DIR', getcwd())
relay_domain = environ.get('RELAY_DOMAIN', 'bitcoiner.social')
relay_admin = environ.get('RELAY_ADMIN', 'blee')
nip05_reserved = [ '_', relay_admin ]

@click.group()
def cli():
    pass

def is_valid_nip05(nip05: str) -> bool:
    # same as email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, nip05) is not None

def get_all_user_profiles() -> list:
    '''Query postgresql to get paid user profiles.'''
    conn = psycopg2.connect(
        host=environ.get("DB_HOST"),
        database=environ.get("DB_NAME"),
        user=environ.get("DB_USER"),
        password=environ.get("DB_PASSWORD")
    )

    cur = conn.cursor()
    # get all kind 0 events, which are user profiles, only for admitted users
    cur.execute("select encode(event_pubkey, 'hex') as pubkey, event_content from events where event_kind=0 and event_pubkey in (select pubkey FROM users WHERE is_admitted is true);")
    profile_results = cur.fetchall()

    # construct a list of all user profiles
    profiles = []
    for result in profile_results:
        profile = json.loads(result[1])
        profile['pubkey'] = result[0]
        profiles.append(profile)

    print(f"Found {len(profiles)} user profiles.")
    return profiles

# super important: it's pronounced "nip-oh-five-ers"
def get_nip05ers() -> dict:
    nip05ers = {}
    for profile in get_all_user_profiles():
        nostr_identifier = profile.get("nip05")
        if nostr_identifier and is_valid_nip05(nostr_identifier) and nostr_identifier.lower().endswith(f"@{relay_domain}"):
            print(f"INTERNAL NIP-05: {nostr_identifier}")
            nip05_user = nostr_identifier.split("@")[0]
            if nip05_user in nip05_reserved:
                continue
            nip05er = { nip05_user: profile.get('pubkey') }
            nip05ers.update(nip05er)
    return nip05ers

@click.command()
def create_nip05_json() -> None:
    # https://websockets.readthedocs.io/en/stable/

    nip05ers = { 
        "_": "111f214dd63c679aa34b102efe774a815594b8271469c6dbe155fc52af872794",
        'blee': '69a0a0910b49a1dbfbc4e4f10df22b5806af5403a228267638f2e908c968228d',
        "ToxiKat27": "12cfc2ec5a39a39d02f921f77e701dbc175b6287f22ddf0247af39706967f1d9",
    }
    nip05ers.update(get_nip05ers())

    nip05_json = {
        "names": nip05ers,
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