def cache_file_get(filepath):
  try:
      with open(filepath) as fp:
          return fp.read()
  except FileNotFoundError:
      return False

def cache_file_write(filepath, content, mode='w'):
    with open(filepath, mode) as fp:
        fp.write(content)
        fp.close()
