# Miro - an RSS based video player application
# Copyright (C) 2005, 2006, 2007, 2008, 2009, 2010, 2011
# Participatory Culture Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the OpenSSL
# library.
#
# You must obey the GNU General Public License in all respects for all of
# the code used other than OpenSSL. If you modify file(s) with this
# exception, you may extend this exception to your version of the file(s),
# but you are not obligated to do so. If you do not wish to do so, delete
# this exception statement from your version. If you delete this exception
# statement from all source files in the program, then also delete it here.


"""Functions to handle moving/deleting files, especially on windows
where file locking semantics can cause problems.
"""

import logging
import os
import shutil

from miro import u3info

from miro.plat.filebundle import is_file_bundle

def makedirs(path):
    path = expand_filename(path)
    return os.makedirs(path)

def isfile(path):
    if not path:
        return False
    path = expand_filename(path)
    return os.path.isfile(path)

def isdir(path):
    if not path:
        return False
    path = expand_filename(path)
    return os.path.isdir(path)

def isabs(path):
    path = expand_filename(path)
    return os.path.isabs(path)

def getctime(path):
    path = expand_filename(path)
    time = os.path.getctime(path)
    # work around python bug - see #15818
    time = max(time, 0) 
    return time

def getmtime(path):
    path = expand_filename(path)
    time = os.path.getmtime(path)
    # work around python bug - see #15818
    time = max(time, 0) 
    return time

def exists(path):
    if not path:
        # DeprecationWarning
        logging.debug("special case used in fileutil.exists(): path=%r", path)
        return False
    path = expand_filename(path)
    return os.path.exists(path)

def remove(path):
    path = expand_filename(path)
    return os.remove(path)

def rmtree(path):
    path = expand_filename(path)
    return shutil.rmtree(path)

def listdir(path):
    path = expand_filename(path)
    return os.listdir(path)

def open_file(path, *args, **kwargs):
    path = expand_filename(path)
    return file(path, *args, **kwargs)

def access(path, *args, **kwargs):
    path = expand_filename(path)
    return os.access(path, *args, **kwargs)

def move(src, dest):
    src = expand_filename(src)
    dest = expand_filename(dest)
    shutil.move(src, dest)

def rmdir(path):
    path = expand_filename(path)
    os.rmdir (path)

def rename(src, dest):
    src = expand_filename(src)
    dest = expand_filename(dest)
    os.rename (src, dest)

def abspath(path):
    path = expand_filename(path)
    path = os.path.abspath(path)
    path = collapse_filename(path)
    return path

def copy_with_progress(input_path, output_path, block_size=32*1024):
    flags = os.O_WRONLY | os.O_CREAT
    if hasattr(os, 'O_SYNC'):
        flags |= os.O_SYNC
    output_fd = os.open(output_path, flags)
    with file(input_path, 'rb') as input:
        with os.fdopen(output_fd, 'wb') as output:
            data = input.read(block_size)
            while data:
                output.write(data)
                result = yield len(data)
                if result:
                    # return True to cancel. NB: you should probably remove the
                    # output file
                    break
                data = input.read(block_size)

try:
    samefile = os.path.samefile
except AttributeError:
    # Windows doesn't have samefile()
    def samefile(path1, path2):
        abspath1 = os.path.normcase(abspath(path1))
        abspath2 = os.path.normcase(abspath(path2))
        return abspath1 == abspath2

def is_windows_file_in_use_error(exception):
    """Check if an exception was caused by a file being in use on windows

    This is for errors like #15312, where we try to delete/move a file on
    windows and fail because of it's filesystem semantics.  To work around
    that we need to check if an error is caused by the windows weirdness, or
    if it's some other filesystem error.
    """
    if not isinstance(exception, Exception):
        raise TypeError("%r is not an exception" % exception)
    # errno 13 is permission denied, windows error 32 is that the file is in
    # use.  For non WindowsErrors winerror isn't set and for non OSErrors,
    # errno isn't set.  If either of those attributes are missing, then we can
    # safely return False
    try:
        return exception.errno == 13 and exception.winerror == 32
    except AttributeError:
        return False

def migrate_file(source, dest, callback, retry_after=10, retry_for=60):
    """Try to migrate a file, if this works, callback is called.  If
    we fail because the file is open, we retry migrating the file
    every so often (by default every 10 seconds, stopping after 60
    seconds).  This probably only makes a difference on Windows.
    """
    import eventloop

    source = expand_filename(source)
    dest = expand_filename(dest)

    try:
        shutil.move(source, dest)
    except EnvironmentError, e:
        logging.warn("Error migrating %s to %s (Error: %s)", source, dest, e)
        try:
            os.remove(dest)
        except EnvironmentError:
            pass
        if retry_for > 0:
            if is_windows_file_in_use_error(e):
                # permission denied, assume this means it's open by
                # another process on windows.
                logging.info('Retrying migration for %s', source)
                eventloop.add_timeout(retry_after, migrate_file,
                        "Migrate File Retry", args=(source, dest, callback,
                            retry_after, retry_for - retry_after))
    except TypeError, e:
        logging.warn ("Type error migrating %s (%s) to %s (%s) (Error %s)",
                source, type(source), dest, type(dest), e)
        raise
    else:
        callback()

class DeletesInProgressTracker(object):
    def __init__(self):
        self.set = set()
    def normalize(self, path):
        return os.path.abspath(os.path.normcase(path))
    def add(self, path):
        self.set.add(self.normalize(path))
    def discard(self, path):
        self.set.discard(self.normalize(path))
    def __contains__(self, path):
        return self.normalize(path) in self.set

deletes_in_progress = DeletesInProgressTracker()

def delete(path, retry_after=10, retry_for=60, firsttime=True):
    """Try to delete a file or directory.  If this fails because the
    file is open, we retry deleting the file every so often This
    probably only makes a difference on Windows.
    """

    import eventloop
    path = expand_filename(path)
    try:
        if os.path.isfile(path):
            os.remove (path)
        elif os.path.isdir(path):
            shutil.rmtree (path)
        else:
            logging.warn("asked to delete '%s' but it's not there." % path)
    except EnvironmentError, e:
        logging.warn("Error deleting %s", path)
        if retry_for > 0 and is_windows_file_in_use_error(e):
            # permission denied, assume this means it's open by another
            # process on windows.
            deletes_in_progress.add(path)
            logging.info('Retrying delete for %s (%d)', path, retry_after)
            eventloop.add_timeout(retry_after, delete,
                    "Delete File Retry", args=(path, retry_after,
                        retry_for - retry_after, False))
            if firsttime:
                logging.debug('restarting subprocess_manager to hopefully '
                              'free file references')
                from miro.workerprocess import _subprocess_manager
                _subprocess_manager.restart(clean=True)

    else:
        deletes_in_progress.discard(path)

def miro_listdir(directory):
    """Directory listing that's safe and convenient for finding new
    videos in a directory.

    Returns the tuple (files, directories) where both elements are a
    list of absolute pathnames.  OSErrors are silently ignored.
    Hidden files aren't returned.  Pathnames are run through
    os.path.normcase.
    """
    # FIXME - this doesn't look used anywhere

    files = []
    directories = []
    expanded_directory = expand_filename(directory)
    expanded_directory = os.path.abspath(os.path.normcase(expanded_directory))
    if expanded_directory in deletes_in_progress:
        return
    try:
        listing = os.listdir(expanded_directory)
    except OSError:
        return [], []
    for name in listing:
        if name[0] == '.' or name.lower() == 'thumbs.db':
            # thumbs.db is a windows file that speeds up thumbnails.
            # We know it's not a movie file.
            continue
        expanded_path = os.path.join(expanded_directory, os.path.normcase(name))
        path = os.path.join(directory, os.path.normcase(name))
        if expanded_path in deletes_in_progress:
            continue
        try:
            if os.path.isdir(expanded_path):
                directories.append(path)
            else:
                files.append(path)
        except OSError:
            pass
    return files, directories

def miro_allfiles(directory, checked=None):
    """Directory listing that's safe and convenient for finding new
    videos in a directory.

    Returns a list of files consisting of absolute pathnames.

    OSErrors are silently ignored.  Hidden files aren't returned.
    Pathnames are run through os.path.normcase.
    """
    if checked is None:
        checked = set()
    expanded_directory = expand_filename(directory)
    expanded_directory = os.path.abspath(os.path.normcase(expanded_directory))
    real_directory = os.path.realpath(expanded_directory)
    if real_directory in checked:
        logging.debug('%s is a symlink to a directory that has '
            'already been checked; skipping', repr(expanded_directory))
        return
    checked.add(real_directory)
    if expanded_directory in deletes_in_progress:
        return
    if is_file_bundle(expanded_directory):
        return
    try:
        listing = os.listdir(expanded_directory)
    except OSError:
        logging.debug('OSError walking directory; continuing', exc_info=1)
        return
    for name in listing:
        name_lower = name.lower()
        if (name.startswith('.') or name_lower == 'thumbs.db' or
                name_lower == "incomplete downloads"):
            # thumbs.db is a windows file that speeds up thumbnails.
            # We know it's not a movie file.
            continue
        path = os.path.join(directory, os.path.normcase(name))
        expanded_path = os.path.join(expanded_directory, os.path.normcase(name))
        if expanded_path in deletes_in_progress:
            continue
        try:
            if (os.path.isdir(expanded_path) and
              not is_file_bundle(expanded_path)):
                for fn in miro_allfiles(path, checked):
                    yield fn
            elif os.path.isfile(expanded_path):
                yield path
        except OSError:
            logging.debug('OSError walking directory; continuing', exc_info=1)
            pass


def expand_filename(filename):
    if not filename:
        return filename
    if u3info.u3_active:
        if filename.startswith(u3info.APP_DATA_PREFIX):
            filename = filename[len(u3info.APP_DATA_PREFIX):]
            while len(filename) > 0 and filename[0] in ['/', '\\']:
                filename = filename[1:]
            if len(filename) == 0:
                return u3info.app_data_path
            return os.path.join (u3info.app_data_path, filename)
        if filename.startswith(u3info.DEVICE_DOCUMENT_PREFIX):
            filename = filename[len(u3info.DEVICE_DOCUMENT_PREFIX):]
            while len(filename) > 0 and filename[0] in ['/', '\\']:
                filename = filename[1:]
            if len(filename) == 0:
                return u3info.device_document_path
            return os.path.join (u3info.device_document_path, filename)
    return filename

def collapse_filename(filename):
    if not filename:
        return filename
    if u3info.u3_active:
        if filename.startswith(u3info.app_data_path):
            filename = filename[len(u3info.app_data_path):]
            while len(filename) > 0 and filename[0] in ['/', '\\']:
                filename = filename[1:]
            if len(filename) == 0:
                return u3info.APP_DATA_PREFIX
            return u3info.APP_DATA_PREFIX + '\\' + filename

        elif filename.startswith(u3info.device_document_path):
            filename = filename[len(u3info.device_document_path):]
            while len(filename) > 0 and filename[0] in ['/', '\\']:
                filename = filename[1:]
            if len(filename) == 0:
                return u3info.DEVICE_DOCUMENT_PREFIX
            return u3info.DEVICE_DOCUMENT_PREFIX + '\\' + filename
    return filename

class FileSet(object):
    """Store a set of files and check if a path is contained.

    The reason this is hard is because of filesystem case issues.  Right now
    we handle it by always comparing files using lowercase.  Eventually we
    should have a better system, see #17108 for discussion
    """

    def __init__(self, initial_files=None):
        self.pathset = set()
        if initial_files:
            for path in initial_files:
                self.add_path(path)

    def add_path(self, path):
        self.pathset.add(path.lower())

    def contains_path(self, path):
        return path.lower() in self.pathset
