import json
import requests
from requests.exceptions import HTTPError

class FileRetriever(object):

    def __init__(self, logger, url, cache_file=None, timeout=2.0):
        self.logger = logger
        self.url = url
        self.cache_file = cache_file
        self.timeout = timeout

    def get_json(self):
        data = self.get()
        if data:
            self.logger.debug("Parsing JSON for : %s" % self.url)
            return self.parse_json(data)
        return False

    def get(self):
        self.logger.debug("Retrieving file from : %s" % self.url)
        try:
            response = requests.get(self.url, timeout=self.timeout)
            response.raise_for_status()
            self.write_cache_file(response.text)
            return response.text
        except Exception as err:
            self.logger.error('Error occurred: %s' % err)
            return self.try_cache_file()

    def write_cache_file(self, data):
        if self.cache_file:
            self.logger.info('Caching data to file: %s' % self.cache_file)
            self.cache_file_write(data)

    def try_cache_file(self):
        if self.cache_file:
            self.logger.info('Trying cache file: %s' % self.cache_file)
            return self.cache_file_get()
        return False

    def cache_file_get(self):
      try:
          with open(self.cache_file) as fp:
              return fp.read()
      except FileNotFoundError:
          return False

    def cache_file_write(self, content, mode='w'):
        with open(self.cache_file, mode) as fp:
            fp.write(content)
            fp.close()

    def parse_json(self, content):
        try:
            data = json.loads(content)
            return data
        except ValueError as e:
            self.logger.error('Could not parse JSON: %s' % e)
            return False
