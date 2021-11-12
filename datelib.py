from time import time
from datetime import datetime, timezone

def iso_utc_date_2epoch(iso_date):
    return int(datetime.strptime(iso_date,"%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp())

def current_iso_date():
    return datetime.utcnow().replace(microsecond=0).isoformat()

def current_unix_timestamp():
    return int(time())
