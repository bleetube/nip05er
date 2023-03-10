import json, logging, re
import click, psycopg2
from os import getcwd
from sys import exit
from pprint import pprint
from dotenv import dotenv_values
config = dotenv_values(f"{getcwd()}/.env")

relay_admin = config.get('RELAY_ADMIN', 'admin')
nip05er_data = config.get('NIP05ER_DATA', getcwd())
relay_domain = config.get('RELAY_DOMAIN', 'bitcoiner.social')
relay_admin = config.get('RELAY_ADMIN', 'blee')
well_known_json = config.get('NIP05ER_JSON', '/var/www/html/.well-known/nostr.json')
nip05er_log = config.get('NIP05ER_LOG_PATH', None)


logging.basicConfig(
    filename=nip05er_log,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
logger = logging.getLogger(__name__)

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
        host=config.get("DB_HOST"),
        database=config.get("DB_NAME"),
        user=config.get("DB_USER"),
        password=config.get("DB_PASSWORD")
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

    logging.info(f"Found {len(profiles)} user profiles.")
    return profiles

# super important: it's pronounced "nip-oh-five-ers"
@click.command()
@click.option('--showvars', is_flag=True, help='Print all environment variables and exit.')
def update(showvars = False) -> dict:
    if showvars:
        pprint(config)
        exit(well_known_json)
    update_json = False
    with open(well_known_json, 'r') as file:
        nostr_json = json.loads(file.read())
    nip05ers = {}
    for profile in get_all_user_profiles():
        nostr_identifier = profile.get("nip05")
        if nostr_identifier and is_valid_nip05(nostr_identifier) and nostr_identifier.lower().endswith(f"@{relay_domain}"):
            local_part = nostr_identifier.split("@")[0]

            # Case insensitive check for existing nip-05ers.
            if any(local_part.lower() == nip05er_name.lower() for nip05er_name in nostr_json.get('names')):
                logging.debug(f"Existing nip-05er: {nostr_identifier}")
                continue

            # Check if this user already has a nip05 entry in our nostr.json
            existing_nip05er = [ local_part for local_part in nostr_json.get('names').keys() if nostr_json.get('names').get(local_part) == profile.get('pubkey') ]
            if existing_nip05er:
                logging.info(f"NIP-05 username changed: {existing_nip05er[0]} -> {local_part}")
                # Remove the old entry before we add the new one.
                nostr_json['names'].pop(existing_nip05er[0])

            logging.warn(f"Adding new nip-05er: {nostr_identifier}")
            # Using a flag here allows us to finish the loop and write all changes to nostr.json at once.
            update_json = True
            new_nip05er = { local_part: profile.get('pubkey') }
            nostr_json['names'].update(new_nip05er)
    if update_json:
        logging.debug(f"Writing updates to {well_known_json}")
        with open(well_known_json, 'w') as file:
            file.write(json.dumps(nostr_json))
        logging.debug(json.dumps(nostr_json))
    return nip05ers

cli.add_command(update)