import json, logging, re
import click, psycopg2
from os import getcwd
from sys import exit
from pprint import pprint
from dotenv import dotenv_values
config = dotenv_values(f"{getcwd()}/.env")
config = dotenv_values('/home/blee/docker/.env')

relay_admin = config.get('RELAY_ADMIN', 'admin')
nip05er_data = config.get('NIP05ER_DATA', getcwd())
relay_domain = config.get('RELAY_DOMAIN', 'bitcoiner.social')
relay_admin = config.get('RELAY_ADMIN', 'blee')
well_known_json = config.get('NIP05ER_JSON', '/var/www/html/.well-known/nostr.json')
log_file = config.get('LOG_PATH', None)


logging.basicConfig(
#   filename=log_file,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
#console = logging.StreamHandler()
#console.setLevel(logging.DEBUG)
#formatter = logging.Formatter('%(levelname)s: %(message)s')
#console.setFormatter(formatter)
#logging.getLogger('').addHandler(console)
#logger = logging.getLogger(__name__)

@click.group()
def cli():
    pass

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

def get_all_users() -> list:
    '''Query postgresql to get paid user profiles.'''
    conn = psycopg2.connect(
        host=config.get("DB_HOST"),
        database=config.get("DB_NAME"),
        user=config.get("DB_USER"),
        password=config.get("DB_PASSWORD")
    )

    cur = conn.cursor()
    # get all kind 0 events, which are user profiles, only for admitted users
    cur.execute("select encode(pubkey, 'hex') as pubkey FROM users WHERE is_admitted is true;")
    profile_results = cur.fetchall()

    # Results are tuples, construct a list.
    profiles = []
    for result in profile_results:
        profiles.append(result[0])

    logging.info(f"Found {len(profiles)} local users.")
    return profiles

def get_reports() -> list:
    '''Query postgresql to get paid user profiles.'''
    conn = psycopg2.connect(
        host=config.get("DB_HOST"),
        database=config.get("DB_NAME"),
        user=config.get("DB_USER"),
        password=config.get("DB_PASSWORD")
    )

    cur = conn.cursor()
    # get all kind 0 events, which are user profiles, only for admitted users
    cur.execute("select event_tags, encode(event_pubkey, 'hex') from events where event_kind = 1984;")
    reports_results = cur.fetchall()

    # Results are tuples, construct a list of the results.
    report_tags = []
    for report_tag_results in reports_results:
        report_entry = dict(report_tag_results[0])
        report_entry['report_author'] = report_tag_results[1]
        report_tags.append(report_entry)
    
    logging.info(f"Found {len(report_tags)} user reports.")
    return report_tags

def show_reports() -> list:
    '''Check for reports against all users.'''
    report_tags = get_reports()
    local_users = get_all_users()
    user_profiles = get_all_user_profiles()
    report_list = []
    for report in report_tags:
        if report.get('p') in local_users:
            # Assign the name from the profile if the user has a name in their profile.
            try: 
                local_user = [profile['name'] for profile in user_profiles if profile.get('pubkey') == report.get('p') and profile.get('name')][0]
                subject_of_report = f"{local_user} ({report.get('p')})"
            except IndexError:
                local_user = report.get('p')
                pass
            try: 
                report_author = [profile['name'] for profile in user_profiles if profile.get('pubkey') == report.get('report_author') and profile.get('name')][0]
                author_of_report = f"{report_author} ({report.get('report_author')})"
            except IndexError:
                author_of_report = report.get('report_author')
                pass
            report_msg = f"Report against {subject_of_report} by {author_of_report}"
            if report.get('report'):
                report_msg += f" for {report.get('report')}"
            if report.get('e'):
                report_msg += f" on event {report.get('e')}"
            logging.info(report_msg)
            report_list.append(report)
    logging.info(f"Found {len(report_list)} reports against users.")
    return report_list

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