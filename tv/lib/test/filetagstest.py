"""This module tests miro.filetags for correct and complete extraction (and
writing - to be implemented) of metadata tags.
"""

try:
    import simplejson as json
except ImportError:
    import json

from miro.test.framework import MiroTestCase, dynamic_test

import shutil
from os import path, stat

from miro.plat import resources
from miro.plat.utils import PlatformFilenameType
from miro.filetags import calc_cover_art_filename, process_file

@dynamic_test(expected_cases=8)
class FileTagsTest(MiroTestCase):
    # mp3-2.mp3:
        # FIXME: losing data - TPE2="Chicago Public Media"

    # drm.m4v:
        # FIXME: losing data - CPRT='\xa9 2002 Discovery Communications Inc.'
        # FIXME: losing data - DESC='When it comes to sorting out some'...
        # FIXME: losing data - LDES='When it comes to sorting out some'...
        # FIXME: we should probably not include an album_artist field when
        # its origin is the same field as artist
        # FIXME: losing data - TVSH='The Most Extreme'
        # FIXME: losing data - TVNN='Animal Planet'

    @classmethod
    def generate_tests(cls):
        results_path = resources.path(path.join('testdata', 'filetags.json'))
        return json.load(open(results_path)).iteritems()

    def dynamic_test_case(self, filename, expected):
        # make all keys unicode
        #expected = dict((unicode(key), value)
                        #for key, value in expected.iteritems())
        filename = resources.path(path.join('testdata', 'metadata', filename))
        results = process_file(filename, self.tempdir)
        # cover art nedes to be handled specially
        cover_art = expected.pop('cover_art')
        if cover_art:
            # cover art should be stored using the album name as its file
            correct_path = path.join(self.tempdir, results['album'])
            self.assertEquals(results.pop('cover_art'), correct_path)
            self.assertEquals(results.pop('created_cover_art'), True)
        else:
            self.assert_('cover_art' not in results)
        # for the rest, we just compare the dicts
        self.assertEquals(results, expected)

    def test_shared_cover_art(self):
        # test what happens when 2 files with coverart share the same album.
        # In this case the first one we process should create the cover art
        # file and the next one should just skip cover art processing.
        src_path = resources.path(path.join('testdata', 'metadata',
                                            'drm.m4v'))
        dest_paths = []
        for x in range(3):
            new_filename = 'drm-%s.m4v' % x
            dest_path = path.join(self.tempdir, new_filename)
            shutil.copyfile(src_path, dest_path)
            dest_paths.append(dest_path)

        # process the first file
        result_1 = process_file(dest_paths[0], self.tempdir)
        self.assertEquals(result_1['cover_art'],
                          path.join(self.tempdir, result_1['album']))
        self.assert_(path.exists(result_1['cover_art']))
        org_mtime = stat(result_1['cover_art']).st_mtime

        # process the rest, they should fill in the cover_art value, but
        # not rewrite the file
        for dup_path in dest_paths[1:]:
            results = process_file(dup_path, self.tempdir)
            self.assertEquals(results['cover_art'],
                              result_1['cover_art'])
            self.assert_(path.exists(results['cover_art']))
            self.assertEquals(stat(results['cover_art']).st_mtime,
                              org_mtime)

@dynamic_test()
class TestCalcCoverArtFilename(MiroTestCase):
    @classmethod
    def generate_tests(cls):
        return [
            (u'Simple Album Name', 'Simple Album Name'),
            (u'Bad/File\0Parts<>:"\\|?*', 
             'Bad%2FFile%00Parts%3C%3E%3A%22%5C%7C%3F%2A'),
            (u'Extended Chars\xf3', 'Extended Chars%C3%B3'),
        ]

    def dynamic_test_case(self, album_name, correct_filename):
        self.assertEquals(calc_cover_art_filename(album_name),
                          correct_filename)
        self.assert_(isinstance(calc_cover_art_filename(album_name),
                     PlatformFilenameType))
