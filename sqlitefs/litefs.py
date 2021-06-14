'''
SQLiteFS Operatiosn Class


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


import fuse
from .coreutils import *
from datetime import datetime
import logging
import errno
from sqlitedict import SqliteDict
from hashlib import blake2s
from base64 import urlsafe_b64encode
from .dope import DOPE2


def blake2_uuid(data: bytes) -> str:
    '''
    BLAKE2S Hash
    '''
    hash_data = blake2s(data).hexdigest()
    return f'{hash_data}'


class SecFS(fuse.LoggingMixIn, fuse.Operations):
    """
    SecFS Filesystem Bridge Programmes written with FUSE
    """
    def __init__(self, name: str, password: bytes, volume_name: str,
                 size: int = 1E9):
        import os
        self.volume_name = volume_name
        self.__password = password
        self.db = SqliteDict(os.path.abspath(
            f"./{name}" + ".db"), autocommit=False, tablename=self.volume_name)
        try:
            self.dopex = DOPE2.marshall(self.db['auth_key'], password)
        except KeyError:
            self.dopex = DOPE2(password, 8219, 32, 'GCM', b'',
                               block_size=512)
            self.db['auth_key'] = self.dopex.serialize()
        try:
            self.dopex.fixate()
            self.FS = load_fs(self.dopex.decode(self.db[volume_name]))
        except KeyError:
            self.db[volume_name] = self.dopex.encode(
                init_fs(volume_name=volume_name, fs_size=int(size)))
            self.dopex = DOPE2.marshall(self.db['auth_key'], password)
            self.dopex.fixate()
            self.FS = load_fs(self.dopex.decode(self.db[volume_name]))
        self.uid = os.getuid()
        self.gid = os.getgid()

    def access(self, path, mode):
        try:
            inode = creeper(path, self.FS)
        except Exception:
            raise fuse.FuseOSError(errno.EFAULT)
        if inode[0xFF]['st_uid'] == self.uid:
            if (inode[0xFF]['st_mode'] >> 6) & mode:
                return 0
            raise fuse.FuseOSError(errno.EACCES)
        elif inode[0xFF]['st_gid'] == self.gid:
            if (inode[0xFF]['st_mode'] >> 3) & mode:
                return 0
            raise fuse.FuseOSError(errno.EACCES)
        else:
            if (inode[0xFF]['st_mode']) & mode:
                return 0
            raise fuse.FuseOSError(errno.EACCES)

    def destroy(self, *args):
        self.db['auth_key'] = self.dopex.serialize()
        self.db[self.volume_name] = self.dopex.encode(dump_fs(self.FS))
        self.db.commit()
        self.db.close()
        pass

    def getattr(self, path, fh=None):
        '''
        Attributes
        '''
        if path[-1] != '/':
            path += '/'
        try:
            inode = creeper(path, self.FS)
            head = inode[0xFF]
            return head
        except KeyError:
            raise fuse.FuseOSError(errno.ENOENT)

    def getxattr(self, path, name, fh=None):
        '''
        eXtended Attributes
        '''
        if path[-1] != '/':
            path += '/'
        inode = creeper(path, self.FS)
        head = inode[0xF7]
        try:
            return head[name] or b''
        except KeyError:
            return b''

    def setxattr(self, path, name, value, size, fh=None):
        '''
        Set eXtended Attributes
        '''
        if path[-1] != '/':
            path += '/'
        inode = creeper(path, self.FS)
        inode[0xF7][name] = value

    def chmod(self, path, mode):
        '''
        Change Mode
        '''
        if path[-1] != '/':
            path += '/'
        inode = creeper(path, self.FS)
        inode[0xFF]['st_mode'] = mode
        return 0

    def chown(self, path, uid, gid):
        '''
        Change Ownership
        '''
        if path[-1] != '/':
            path += '/'
        inode = creeper(path, self.FS)
        inode[0xFF]['st_uid'] = uid
        inode[0xFF]['st_gid'] = gid
        return 0

    def create(self, path, mode):
        '''
        touch core
        '''
        if path[-1] != '/':
            path += '/' + '~'
        time_var = datetime.now()
        dir_inode = {
            0xFF: {
                'st_mode': mode,
                'st_uid': self.uid,
                'st_gid': self.gid,
                'st_nlink': 0x01,
                'st_size': 4096,
                'st_ctime': time_var.timestamp(),
                'st_atime': time_var.timestamp(),
                'st_mtime': time_var.timestamp()
            },
            0xF7: {

            }
        }
        if mode & REGF:
            dir_inode[0x7F] = {
                0: b''
            }
            dir_inode[0xFF]['st_size'] = 0
        seeper(path, self.FS, dir_inode)
        return 1

    def flush(self, path, fh):
        '''
        Flush Commit
        '''
        if path[-1] != '/':
            path += '/'
        inode = creeper(path, self.FS)
        uuid_inode = blake2_uuid(path.encode('utf8'))
        if uuid_inode not in self.db:
            inode[0x7E] = uuid_inode
            self.db[uuid_inode] = {}
        data = self.db[inode[0x7E]]
        data.update(inode[0x7F])
        data = dict(filter(lambda x: x[0] < inode[0xFF]['st_size'],
                           data.items()))
        self.db[inode[0x7E]] = data
        inode[0x7F] = {}
        self.dopex.fixate()
        self.db[self.volume_name] = self.dopex.encode(dump_fs(self.FS))
        return 0

    def fsync(self, path, datasync, fh):
        '''
        Sync Force Commit
        '''
        self.dopex.fixate()
        self.db[self.volume_name] = self.dopex.encode(dump_fs(self.FS))
        self.db.commit()
        return 0

    def readdir(self, path, fh):
        '''
        ls core
        '''
        if path[-1] != '/':
            path += '/'
        return ['.', '..'] + lister(path, self.FS)

    def mkdir(self, path, mode):
        '''
        Make Directories
        '''
        if path[-1] != '/':
            path += '/' + '~'
        time_var = datetime.now()
        dir_inode = {
            0xFF: {
                'st_mode': mode + DIRT,
                'st_uid': self.uid,
                'st_gid': self.gid,
                'st_nlink': 0x01,
                'st_size': 4096,
                'st_ctime': time_var.timestamp(),
                'st_atime': time_var.timestamp(),
                'st_mtime': time_var.timestamp()
            },
            0xF7: {

            }
        }
        seeper(path, self.FS, dir_inode)

    def read(self, path, size, offset, fh):
        '''
        Read Data
        '''
        if path[-1] != '/':
            path += '/'
        inode = creeper(path, self.FS)
        try:
            if inode[0x7F] != {}:
                dopex = DOPE2.marshall(self.db['auth_key'], self.__password)
                dopex.fixate()
                data_buff = b''.join([dopex.decode(inode[0x7F][x])
                                      for x in inode[0x7F]
                                      if x >= offset and x <= offset + size])
                del dopex
                return data_buff[:size]
            elif 0x7E in inode:
                dopex = DOPE2.marshall(self.db['auth_key'], self.__password)
                dopex.fixate()
                inode[0x7F] = self.db[inode[0x7E]]
                data_buff = b''.join([dopex.decode(inode[0x7F][x])
                                      for x in inode[0x7F]
                                      if x >= offset and x <= offset + size])
                del dopex
                return data_buff[:size]
            else:
                return b''
        except KeyError:
            raise fuse.FuseOSError(errno.EISDIR)

    def write(self, path, data, offset, fh):
        '''
        Journal Writing
        '''
        if path[-1] != '/':
            path += '/'
        inode = creeper(path, self.FS)
        if 0x7E not in inode:
            inode[0x7E] = blake2_uuid(path.encode('utf8'))
            self.db[inode[0x7E]] = {}
        try:
            dopex = DOPE2.marshall(self.db['auth_key'], self.__password)
            dopex.fixate()
            inode[0x7F][offset] = dopex.encode(data)
            inode[0xFF]['st_size'] += len(data)
            self.FS[0xF8]['f_bfree'] -= int(len(data) / 512)\
                if len(data) / 512 >= 1 else 0
            self.FS[0xF8]['f_ffree'] -= int(len(data) / 4096)\
                if len(data) / 4096 >= 1 else 0
            self.FS[0xF8]['f_favail'] -= int(len(data) / 4096)\
                if len(data) / 4096 >= 1 else 0
            self.FS[0xF8]['f_bavail'] -= int(len(data) / 512)\
                if len(data) / 512 >= 1 else 0
            del dopex
            return len(data)
        except KeyError:
            return 0

    def rename(self, old, new):
        '''
        Rename
        '''
        if old[-1] != '/':
            old += '/'
        inode = creeper(old, self.FS)
        if new[-1] != '/':
            new += '/'
        seeper(new+'~', self.FS, inode)
        if blake2_uuid(old.encode('utf8')) in self.db:
            self.db[blake2_uuid(new.encode('utf8'))] = self.db[
                blake2_uuid(old.encode('utf8'))
            ]
        sweeper(old, self.FS)
        return 0

    def rmdir(self, path):
        '''
        Remove Directory
        '''
        if path[-1] != '/':
            path += '/'
        dir_list = lister(path, self.FS)
        if len(dir_list) > 0:
            raise fuse.FuseOSError(errno.ENOTEMPTY)
        else:
            sweeper(path, self.FS)

    def removexattr(self, path, name):
        '''
        Remove eXtended Attributes
        '''
        if path[-1] != '/':
            path += '/'
        inode = creeper(path, self.FS)
        inode[0xF7].pop(name, None)

    def truncate(self, path, length, fh=None):
        '''
        Truncate Files
        '''
        if path[-1] != '/':
            path += '/'
        inode = creeper(path, self.FS)
        if 0x7F in inode:
            if inode[0x7F] != {}:
                data_buff = b''.join([inode[0x7F][x] for x in inode[0x7F]])
                data_buff = data_buff[:length]
                inode[0x7F] = {x: data_buff[x:x+4096]
                               for x in range(0, len(data_buff), 4096)}
            else:
                if 0x7E in inode:
                    dopex = DOPE2.marshall(self.db['auth_key'], self.__password)
                    dopex.fixate()
                    data_buff = b''.join([dopex.decode(inode[0x7F][x])
                                          for x in self.db[inode[0x7E]]])
                    data_buff = data_buff[:length]
                    inode[0x7F] = {x: data_buff[x:x+4096]
                                   for x in range(0, len(data_buff), 4096)}
            size = (inode[0xFF]['st_size'] - length)
            self.FS[0xF8]['f_bfree'] += int(size / 512)\
                if size / 512 >= 1 else 0
            self.FS[0xF8]['f_ffree'] += int(size / 4096)\
                if size / 4096 >= 1 else 0
            self.FS[0xF8]['f_favail'] += int(size / 4096)\
                if size / 4096 >= 1 else 0
            self.FS[0xF8]['f_bavail'] += int(size / 512)\
                if size / 512 >= 1 else 0
            inode[0xFF]['st_size'] = length
        else:
            raise fuse.FuseOSError(errno.EISDIR)

    def utimens(self, path, times):
        '''
        Time Updates
        '''
        time_var = datetime.now()
        atime, mtime = times if times else (time_var, time_var)
        if path[-1] != '/':
            path += '/'
        inode = creeper(path, self.FS)
        inode[0xFF]['st_atime'] = atime
        inode[0xFF]['st_mtime'] = mtime

    def unlink(self, path):
        '''
        Unlink
        '''
        if path[-1] != '/':
            path += '/'
        inode = creeper(path, self.FS)
        if blake2_uuid(path.encode('utf8')) in self.db:
            size = inode[0xFF]['st_size']
            self.FS[0xF8]['f_bfree'] += int(size / 512)\
                if size / 512 >= 1 else 0
            self.FS[0xF8]['f_ffree'] += int(size / 4096)\
                if size / 4096 >= 1 else 0
            self.FS[0xF8]['f_favail'] += int(size / 4096)\
                if size / 4096 >= 1 else 0
            self.FS[0xF8]['f_bavail'] += int(size / 512)\
                if size / 512 >= 1 else 0
            del self.db[blake2_uuid(path.encode('utf8'))]
        sweeper(path, self.FS)

    def statfs(self, path):
        return self.FS[0xF8]
