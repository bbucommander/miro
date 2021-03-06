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

"""Controller for the Guide tab.  It's a browser with an informational sidebar.
"""
import logging
import operator

from miro.gtcache import gettext as _

from miro import app
from miro import messages

from miro.frontends.widgets import imagebutton
from miro.frontends.widgets import imagepool
from miro.frontends.widgets import widgetutil

from miro.plat import resources
from miro.plat.frontends.widgets import widgetset

class GuideSidebarExpander(widgetset.CustomButton):
    SIDEBAR_BG = imagepool.get_surface(
        resources.path('images/guide-sidebar.png'))
    SIDEBAR_ARROW_OPEN = imagepool.get_surface(
        resources.path('images/guide-sidebar-arrow-open.png'))
    SIDEBAR_ARROW_CLOSE = imagepool.get_surface(
        resources.path('images/guide-sidebar-arrow-close.png'))

    def __init__(self):
        widgetset.CustomButton.__init__(self)
        self.expanded = True

    def size_request(self, layout):
        return 8, -1

    def set_expanded(self, value):
        if value != self.expanded:
            self.expanded = value
            self.queue_redraw()

    def draw(self, context, layout):
        self.SIDEBAR_BG.draw(context, 0, 0, 8, context.height)
        if self.expanded:
            image = self.SIDEBAR_ARROW_CLOSE
        else:
            image = self.SIDEBAR_ARROW_OPEN
        vpos = int((context.height - image.height) / 2)
        hpos = int((8 - image.width) / 2)
        image.draw(context, hpos, vpos, image.width, image.height)

class GuideSidebarCollection(widgetset.VBox):
    WIDTH = 138
    ITEM_LIMIT = 6

    def __init__(self, title, sort_key):
        widgetset.VBox.__init__(self)
        self.current_limit = self.ITEM_LIMIT
        hbox = widgetset.HBox()
        label = widgetset.Label(title.upper())
        label.set_size(0.7)
        label.set_color((0.5, 0.5, 0.5))
        hbox.pack_start(widgetutil.align_left(label), expand=True)
        self.pack_start(widgetutil.pad(hbox, top=20, bottom=10))

        self.item_box = widgetset.VBox(spacing=8) # we want 17px of padding, so
                                                  # 17/2 is close to 8
        self.pack_start(self.item_box)

        self.items = {}
        self.currently_packed = []
        self.sorter = operator.attrgetter(sort_key)

    def set_limit(self, limit):
        if limit > self.ITEM_LIMIT:
            limit = self.ITEM_LIMIT
        if self.current_limit < limit:
            self.current_limit = limit
            self.resort()
        else:
            self.current_limit = limit
            self.currently_packed = self.currently_packed[:limit]
            self.repack()

    def get_label_for(self, text):
        goal = self.WIDTH - 34
        label = widgetset.Label(text)
        label.set_size(0.8)
        if label.get_width() < goal:
            return label
        while True:
            text = text[:-4] + u'...'
            label = widgetset.Label(text)
            label.set_size(0.8)
            if label.get_width() < goal:
                return label

    def get_hbox_for(self, info):
        hbox = widgetset.HBox()
        hbox.pack_start(self.get_label_for(info.name))
        button = imagebutton.ImageButton('guide-sidebar-play')
        button.connect('clicked', self.on_play_clicked, info)
        hbox.pack_end(button)
        return hbox

    def repack(self):
        for child in list(self.item_box.children):
            self.item_box.remove(child)
        for info in self.currently_packed:
            self.item_box.pack_start(self.get_hbox_for(info))

    def resort(self):
        # XXX how do we get data where self.sorter(item) is None!? #17431 is
        # for tracking this issue
        self.currently_packed = list(sorted(
            (item for item in self.items.values() if self.sorter(item)),
            key=self.sorter,
            reverse=True))[:self.current_limit]
        self.repack()

    def set_items(self, items):
        self.items = {}
        for info in items:
            self.items[info.id] = info
        self.resort()

    def add(self, info):
        self.items[info.id] = info
        if len(self.currently_packed) < self.current_limit:
            self.currently_packed.append(info)
            self.currently_packed.sort(key=self.sorter, reverse=True)
            self.repack()
        else:
            self.resort()

    def change(self, info):
        self.items[info.id] = info
        self.resort()

    def remove(self, id_):
        info = self.items.pop(id_)
        if info in self.currently_packed:
            self.resort()

    def on_play_clicked(self, button, info):
        messages.PlayMovie([info]).send_to_frontend()


class GuideSidebarDetails(widgetset.SolidBackground):
    def __init__(self):
        widgetset.SolidBackground.__init__(self)
        self.set_background_color(widgetutil.css_to_color('#e7e7e7'))
        self.video = GuideSidebarCollection(_("Recently Watched"),
                                            'last_watched')
        self.audio = GuideSidebarCollection(_("Recently Listened To"),
                                            'last_watched')
        self.download = GuideSidebarCollection(_("Recent Downloads"),
                                               'downloaded_time')
        self.vbox = widgetset.VBox()
        self.vbox.pack_start(self.video)
        self.vbox.pack_start(self.audio)
        self.vbox.pack_start(self.download)
        self.add(widgetutil.pad(self.vbox, left=17, right=17))

        self.id_to_collection = {}

        self.changing_size = False
        self.current_height = None
        self.connect('size-allocated', self.on_size_allocated)

        self.set_size_request(172, 220)

    def on_size_allocated(self, widget, width, height):
        """
        If our height changes, tell the collections to limit their items.
        """
        if height == self.current_height:
            return
        if self.changing_size:
            return
        self.changing_size = True
        self.current_height = height
        # 35 is the height of the title, 33 is each item's height
        item_count = int(((height / 3 - 35) / 33))
        self.video.set_limit(item_count)
        self.audio.set_limit(item_count)
        self.download.set_limit(item_count)
        self.changing_size = False

    def collection_for(self, info):
        if not info.last_watched:
            return self.download
        elif info.file_type == 'audio':
            return self.audio
        else:
            return self.video

    def on_item_list(self, items):
        collections = {}
        self.id_to_collection = {}
        for info in items:
            collection = self.collection_for(info)
            self.id_to_collection[info.id] = collection
            collections.setdefault(collection, [])
            collections[collection].append(info)

        for collection, items in collections.items():
            collection.set_items(items)

    def on_item_changed(self, added, changed, removed):
        for info in added:
            collection = self.collection_for(info)
            self.id_to_collection[info.id] = collection
            collection.add(info)

        for id_ in removed:
            collection = self.id_to_collection.pop(id_)
            collection.remove(id_)

        for info in changed:
            # if the collection that the info was is changed, send an
            # add/remove pair, otherwise update the info
            collection = self.collection_for(info)
            if collection != self.id_to_collection.get(info.id):
                # bz:17684 self.id_to_collection.get() could return None while
                # collection_for() always return valid value, so we will hit
                # this path.  If there's nothing in the id_to_collection
                # mapping just add.
                try:
                    self.id_to_collection[info.id].remove(info.id)
                except KeyError:
                    logging.error('ItemInfo %s not in id_to_collection map',
                                  repr(info))
                collection.add(info)
                self.id_to_collection[info.id] = collection
            else:
                collection.change(info)

class GuideSidebar(widgetset.HBox):

    def __init__(self):
        widgetset.HBox.__init__(self)
        expander = GuideSidebarExpander()
        expander.connect('clicked', self.on_expander_clicked)
        self.pack_start(expander)

        self.details = GuideSidebarDetails()
        if app.widget_state.get_guide_sidebar_expanded():
            self.pack_start(self.details)
        else:
            expander.set_expanded(False)

    def on_expander_clicked(self, expander):
        if expander.expanded: # we're open, let's close
            self.remove(self.details)
        else:
            self.pack_start(self.details)
        app.widget_state.set_guide_sidebar_expanded(not expander.expanded)
        expander.set_expanded(not expander.expanded)

class GuideTab(widgetset.HBox):

    def __init__(self, browser):
        widgetset.HBox.__init__(self)

        self.browser = browser
        self.sidebar = GuideSidebar()
        self.pack_start(browser, expand=True)
        self.pack_start(self.sidebar)

    def on_item_list(self, items):
        self.sidebar.details.on_item_list(items)

    def on_item_changed(self, added, changed, removed):
        self.sidebar.details.on_item_changed(added, changed, removed)
