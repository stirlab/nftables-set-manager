import re
import datelib
import json
from file_retriever import FileRetriever

IPV4_REGEX = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
CACHE_DIR_DEFAULT = "/tmp"
CACHE_DURATION_DEFAULT = 86400 # One day.

class Plugin(object):

    def __init__(self, metadata, resolver, logger, config, args):
        self.metadata = metadata
        self.resolver = resolver
        self.logger = logger
        self.config = config
        self.args = args
        self.cache_dir = 'cache_dir' in metadata and metadata['cache_dir'] or CACHE_DIR_DEFAULT
        self.cache_duration = 'cache_duration' in metadata and int(metadata['cache_duration']) or CACHE_DURATION_DEFAULT

    def is_ipv4_address(self, hostname):
        return bool(re.match(IPV4_REGEX, hostname))

    def cache_ips(self):
        return self.cache_duration > 0

    def rebuild_cached_ips(self, filename, ips):
        self.logger.debug("Fetching cached IPs for: %s, new IPs: %s" % (filename, ips))
        cache_file = "%s/%s.cached.json" % (self.cache_dir, filename)
        file_retriever = FileRetriever(self.logger, cache_file, cache_file)
        cached_ips = file_retriever.get_json() or {}
        current_iso_date = datelib.current_iso_date()
        expiry_threshold_timestamp = datelib.current_unix_timestamp() - self.cache_duration
        self.logger.debug("Previously cached IPs for %s: %s -- duration: %d" % (filename, cached_ips, self.cache_duration))
        #for k, v in cached_ips.items():
        #    self.logger.debug("IP %s, cached %s, expiry %s" % (k, datelib.iso_utc_date_2epoch(v), expiry_threshold_timestamp))
        cached_ips = {k: v for k, v in cached_ips.items() if datelib.iso_utc_date_2epoch(v) > expiry_threshold_timestamp}
        #self.logger.debug("Cleaned cache IPs for %s: %s" % (filename, cached_ips))
        for ip in ips:
            #self.logger.debug("Caching IP %s for: %s" % (ip, filename))
            cached_ips[ip] = current_iso_date
        self.logger.debug("Full cache list for %s: %s" % (filename, cached_ips))
        file_retriever.write_cache_file(json.dumps(cached_ips, indent=2))
        return cached_ips.keys()
