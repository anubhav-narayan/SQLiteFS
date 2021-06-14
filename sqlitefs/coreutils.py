'''
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
from datetime import datetime
import dill as pickle
from os import listdir, getgid, getuid


SOCK = 0o0140000
LINK = 0o0120000
REGF = 0o0100000
BLOK = 0o0060000
DIRT = 0o0040000
CHRD = 0o0020000
FIFO = 0o0010000
SUID = 0o0004000
SGID = 0o0002000
SVTX = 0o0001000
RWXU = 0o0000700
RUSR = 0o0000400
WUSR = 0o0000200
XUSR = 0o0000100
RWXG = 0o0000070
RGRP = 0o0000040
WGRP = 0o0000020
XGRP = 0o0000010
RWXO = 0o0000007
ROTH = 0o0000004
WOTH = 0o0000002
XOTH = 0o0000001

F_OK = 0
R_OK = 4
W_OK = 2
X_OK = 1


def init_fs(volume_name: str, fs_size: int):
    '''
    Create a new volume in the filesystem
    '''
    time_var = datetime.now()
    group = getgid()
    user = getuid()
    root = {
        0xFF: {
            'st_mode': DIRT | RWXU | RGRP | WGRP | ROTH,
            'st_uid': user,
            'st_gid': group,
            'st_nlink': 0x01,
            'st_size': 4096,
            'st_ctime': time_var.timestamp(),
            'st_atime': time_var.timestamp(),
            'st_mtime': time_var.timestamp()
        },
        0xF8: {
            'f_flags': 4096,
            'f_bsize': 512,
            'f_blocks': fs_size // 512,
            'f_bfree': fs_size // 512,
            'f_bavail': fs_size // 512,
            'f_frsize': 512,
            'f_files': fs_size // 4096,
            'f_favail': fs_size // 4096,
            'f_ffree': fs_size // 4096,
            'f_namemax': 4096,
            'f_namelen': 4096
        },
        0xF7: {

        },
        '': {
            0xFF: {
                'st_mode': DIRT | RWXU | RGRP | WGRP | ROTH,
                'st_uid': user,
                'st_gid': group,
                'st_nlink': 0x01,
                'st_size': 4096,
                'st_ctime': time_var.timestamp(),
                'st_atime': time_var.timestamp(),
                'st_mtime': time_var.timestamp()
            },
            0xF7: {

            },
            '.Trash': {
                0xFF: {
                    'st_mode': DIRT | RWXU | RGRP | WGRP | ROTH,
                    'st_uid': user,
                    'st_gid': group,
                    'st_nlink': 0x01,
                    'st_size': 4096,
                    'st_ctime': time_var.timestamp(),
                    'st_atime': time_var.timestamp(),
                    'st_mtime': time_var.timestamp()
                },
                0xF7: {

                },
            },
            '.Trash-1000': {
                0xFF: {
                    'st_mode': DIRT | RWXU | RGRP | WGRP | ROTH,
                    'st_uid': user,
                    'st_gid': group,
                    'st_nlink': 0x01,
                    'st_size': 4096,
                    'st_ctime': time_var.timestamp(),
                    'st_atime': time_var.timestamp(),
                    'st_mtime': time_var.timestamp()
                },
                0xF7: {

                },
            },
            '.hidden': {
                0xFF: {
                    'st_mode': DIRT | RWXU | RGRP | WGRP | ROTH,
                    'st_uid': user,
                    'st_gid': group,
                    'st_nlink': 0x01,
                    'st_size': 4096,
                    'st_ctime': time_var.timestamp(),
                    'st_atime': time_var.timestamp(),
                    'st_mtime': time_var.timestamp()
                },
                0xF7: {

                },
            },
        }
    }
    root = pickle.dumps(root)
    return root
    pass


def load_fs(fsdump):
    return pickle.loads(fsdump)


def dump_fs(fs):
    return pickle.dumps(fs)


def path_split(path):
    '''
    Split path string to list of keys
    Args:
        path: str - Path String

    Returns:
        list - Key List
    '''
    if path[-1] == '/':
        path = path[:-1]
    path = path.split('/')
    return path


def path_weave(path_list):
    '''
    Convert path list to string
    '''
    if len(path_list) == 0:
        return '/'
    path_ = ''
    for x in path_list:
        path_ += x + '/'
    return path_


def creeper(path, hash_table):
    '''
    Creeps into directories and finds data
    CAUTION: THIS FUNCTION IS RECURSIVE
    Args:
        path: str - Absolute Path String
        hash_table: dict - Hash Table to Creep

    Returns:
        * - Path Value

    Raises:
        KeyError - If path does not exist
    '''
    path = path_split(path)
    if len(path) == 1:
        if path[0] in hash_table:
            return hash_table[path[0]]
        else:
            raise KeyError(f'Directory \'{path[0]}\' does not exist')
    else:
        if path[0] in hash_table:
            if hash_table[path[0]][0xFF]['st_mode'] & DIRT:
                return creeper(path_weave(path[1:]), hash_table[path[0]])
            else:
                raise ValueError(f'\'{path[0]}\' is not a Directory')
        else:
            raise KeyError(f'Directory \'{path[0]}\' does not exist')


def sweeper(path, hash_table):
    '''
    Sweeps into directories and removes data
    CAUTION: THIS FUNCTION IS RECURSIVE
    Args:
        path: str - Absolute Path String
        hash_table: dict - Hash Table to Sweep

    Returns:
        * - Path Value

    Raises:
        KeyError - If path does not exist
    '''
    path = path_split(path)
    if len(path) == 1:
        if path[0] in hash_table:
            if hash_table[0xFF]['st_mode'] & WUSR:
                return hash_table.pop(path[0])
            else:
                raise TypeError('Can\'t Write in this Directory')
        else:
            raise KeyError(f'Directory \'{path[0]}\' does not exist')
    else:
        if path[0] in hash_table:
            if hash_table[path[0]][0xFF]['st_mode'] & 0x80:
                return sweeper(path_weave(path[1:]), hash_table[path[0]])
            else:
                raise ValueError(f'\'{path[0]}\' is not a Directory')
        else:
            raise KeyError(f'Directory \'{path[0]}\' does not exist')


def peeper(path, hash_table):
    '''
    Peeps into directories and finds if that exist
    CAUTION: THIS FUNCTION IS RECURSIVE
    Args:
        path: str - Absolute Path String
        hash_table: dict - Hash Table to Creep

    Returns:
        bool - True if path found else False
    '''
    path = path_split(path)
    if len(path) == 1:
        if path[0] in hash_table:
            return True
        else:
            return False
    else:
        if path[0] in hash_table:
            if hash_table[path[0]][0xFF]['st_mode'] & DIRT:
                return peeper(path_weave(path[1:]), hash_table[path[0]])
            else:
                raise ValueError(f'\'{path[0]}\' is not a Directory')
        else:
            return False


def seeper(path, hash_table, value={}):
    '''
    Seeps directories in the Hash Table
    CAUTION: THIS FUNCTION IS RECURSIVE
    Args:
        path: str - Absolute Path String
        hash_table: dict - Hash Table to Seep

    Returns:
        * - Path Value
    '''
    path = path_split(path)
    hash_table[0xFF]['st_atime'] = datetime.now().timestamp()
    if len(path) == 2 and path[1] == '~':
        if hash_table[0xFF]['st_mode'] & WUSR:
            hash_table[path[0]] = value
            hash_table[0xFF]['st_mtime'] = datetime.now().timestamp()
            return hash_table
        else:
            raise TypeError('Can\'t Write in this Directory')
    else:
        if path[0] in hash_table:
            if hash_table[0xFF]['st_mode'] & WUSR:
                seeper(path_weave(path[1:]), hash_table[path[0]], value)
                hash_table[0xFF]['st_mtime'] = datetime.now().timestamp()
            else:
                raise TypeError('Can\'t Write in this Directory')
        else:
            time_var = datetime.now()
            hash_table[path[0]] = {
                0xFF: {
                    'st_mode': DIRT | RWXU | RGRP | WGRP | ROTH,
                    'st_uid': hash_table[0xFF]['st_uid'],
                    'st_gid': hash_table[0xFF]['st_gid'],
                    'st_nlink': 0x01,
                    'st_size': 4096,
                    'st_ctime': time_var.timestamp(),
                    'st_atime': time_var.timestamp(),
                    'st_mtime': time_var.timestamp()
                }
            }
            del time_var  # Misuse Prevntion
            seeper(path_weave(path[1:]), hash_table[path[0]], value)
            hash_table[0xFF]['st_mtime'] = datetime.now().timestamp()


def lister(path, hash_table):
    '''
    Lists Directories
    Args:
        path: str - Absolute Path String
        hash_table: dict - Hash Table to Seek

    Returns:
        [] - Directories/Files
    '''
    inode = creeper(path, hash_table)
    return [x for x in inode if type(x) == str]
