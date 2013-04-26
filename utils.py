# coding: utf-8

from flask import safe_join
from werkzeug import secure_filename
from hashlib import sha1
import os


def slugify(value):
    """
    Normalizes a string using unidecode library. Lowercase it, remove
    punctuation and replace spacing with hyphens.

    >>> slugify(u'Blåbærsyltetøy')
    'Blabaersyltetoy'
    """
    from unidecode import unidecode
    import re

    value = unidecode(value)
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return unicode(re.sub('[-\s]+', '-', value))

def githash(data):
    length = len(data)
    hsh = sha1()
    hsh.update("blob %u\0" % length)
    hsh.update(data)
    return hsh.hexdigest(), length

def save_file(reqfile, path):
    reqfile_path = safe_join(path, secure_filename(reqfile.filename))
    reqfile.save(reqfile_path)
    with file(reqfile_path) as __f:
        ghash, length = githash(__f.read())
    new_dir = safe_join(path, ghash[0:2])
    new_filename = ghash[2:40]
    new_path = safe_join(new_dir, new_filename)
    try:
        os.makedirs(new_dir)
    except OSError:
        pass  # dir already exists: OK
    os.rename(reqfile_path, new_path)
    return safe_join(ghash[0:2], ghash[2:40]), length
