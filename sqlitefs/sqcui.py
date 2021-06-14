#!/usr/bin/env python3
'''
SQLiteFS Manager Utility


MIT License

Copyright (c) 2021 Anubhav Mattoo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from litefs import (
    fuse,
    logging,
    SecFS,
    SqliteDict,
)
import os
import npyscreen
from coreutils import load_fs
from configparser import ConfigParser
import curses
from daemonocle import Daemon
from base64 import urlsafe_b64encode
from dope import DOPE2
config = ConfigParser()
config.read('config.ini')

volumes = [x for x in config if x != 'DEFAULT']


class FS_ManApp(npyscreen.StandardApp):
    def __init__(self):
        super(npyscreen.StandardApp, self).__init__()
        self.event_directory = {}
        self.event_queues = {}
        self.initalize_application_event_queues()
        self.initialize_event_handling()

    def onStart(self):
        self.Main_Form = self.addForm("MAIN", Main_Form)
        self.Pop_Ups = self.addForm("POP", Popups)

    def process_event_queues(self, max_events_per_queue=None):
        for queue in self.event_queues.values():
            try:
                for event in queue.get(maximum=max_events_per_queue):
                    try:
                        self.process_event(event)
                    except StopIteration:
                        pass
            except RuntimeError:
                pass


class Popups(npyscreen.Popup):
    def create(self):
        self.name = 'Popup'

    def on_ok(self):
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


class Main_Form(npyscreen.FormBaseNew):
    def create(self):
        exit_handlers = {
            '^Q': lambda x: exit(0),
            155: lambda x: exit(0),
            curses.ascii.ESC: lambda x: exit(0),
            '^U': lambda x: self.uload_fstat(),
            '^F': lambda x: self.load_fstat()
        }

        self.name = 'SQLiteFS Manager Utility'
        self.center_on_display()

        self.add_handlers(exit_handlers)

        self.add_event_hander('load_fstat', self.load_fstat)

        x, y = self.useable_space()

        self.volumes = self.add(Volume_Box, name='Volumes',
                                relx=1, max_width = x//2, rely=1)

        self.props = self.add(Props_Box, name='Filesystem Properties',
                              relx=(x//2)+1, rely=1)

        self.volumes.create()
        self.props.create()

    def display_menu_at(self):
        return self.lines - 1, 1

    def draw_form(self):
        super(Main_Form, self).draw_form()
        menu = "^Q : EXIT\t^F : Load FSTAT"
        if isinstance(menu, bytes):
            menu = menu.decode('utf-8', 'replace')
        y, x = self.display_menu_at()
        self.add_line(y, x,
                      menu,
                      self.make_attributes_list(menu, curses.A_NORMAL),
                      self.columns - x - 1)

    def load_fstat(self, *args, **kwds):
        self.props.load_fstat(value=self.volumes.value)

    def uload_fstat(self, *args, **kwds):
        self.props.db.close()
        del self.props.db
        del self.props.fs
        del self.props.fstat
        self.props.values = None
        self.props.volume = None
        self.props.update()


class Volume_Box(npyscreen.BoxTitle):
    def create(self):
        self.display()
        self.values = volumes
        self.update()


class Props_Box(npyscreen.BoxTitle):
    def create(self):
        self.display()

    def load_fstat(self, *args, **kwds):
        value = volumes[kwds['value']]
        self.volume = config[value]['VOLUME_NAME']
        self.db = SqliteDict(os.path.abspath(f"./{value}.db"), autocommit=False, tablename=self.volume)
        self.dopex = DOPE2.marshall(self.db['auth_key'], b'test')
        self.dopex.fixate()
        self.fs = load_fs(self.dopex.decode(self.db[self.volume]))
        self.fstat = self.fs[0xF8]
        self.values = [f'Volume Name : {self.volume}',
                       f'Block Size : {self.fstat["f_bsize"]}',
                       f'Files Stored : {len(self.db) - 2}',
                       f'Size of Storage : {self.fstat["f_blocks"]*512/1E9:.4f} GB',
                       f'Storage Used : {(self.fstat["f_blocks"] - self.fstat["f_bfree"])*512/1E9:.4f} GB',
                       f'On-Disk : {getattr(os.stat(f"./{value}.db"), "st_size")/1E9:.4f} GB']
        self.update()


if __name__ == '__main__':
    FS_ManApp().run()
