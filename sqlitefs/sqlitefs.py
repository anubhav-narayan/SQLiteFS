#!/usr/bin/env python3
'''
SQLiteFS FUSE Mount Utility


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


from .litefs import (
    fuse,
    logging,
    SecFS,
    SqliteDict,
    init_fs,
    load_fs,
    dump_fs
)
from .dope import DOPE2
import click
import sys
import os
from functools import partial
from daemonocle import Daemon


@click.group()
def cli():
    pass


@cli.command(short_help='Create a New Volume', help='Volume Creator')
@click.argument('name', type=str)
@click.option('-m', '--mount', prompt='Mount Point',
              help='Specify Mountpoint Path', type=click.Path())
@click.option('-v', '--volume-name', help='Specify Volume Name', type=str,
              prompt='Volume Name', default=os.getlogin(), show_default=True)
@click.option('-d', '--debug',
              help='Enable Detail Debug(May Require Excess Space)',
              type=bool, default=False, prompt='Debug Mode', is_flag=True)
@click.option('-q', '--quota', help='Data Quota for the Volume in MB',
              type=float, default=1E3, prompt='Volume Size Quota(MB)',
              show_default=True)
@click.password_option()
def init(name, mount, volume_name, debug, quota, password):
    from configparser import ConfigParser
    config = ConfigParser()
    config.read(os.path.abspath(f'~/.sqlitefs/config.ini'))
    config[name] = {
        'VOLUME_NAME': volume_name,
        'MOUNT': os.path.abspath(mount),
        'DEBUG': debug,
        'SIZE': quota
    }
    with open(os.path.abspath(f'~/.sqlitefs/config.ini'), 'w') as file:
        config.write(file)
    if not os.path.exists(os.path.abspath(mount)):
        os.mkdir(os.path.abspath(mount))
    quota = int(quota * 1E6)
    if os.path.exists(os.path.join(
                os.environ['HOME'],
                '.sqlitefs',
                f'{name}.db')):
        raise click.ClickException(f'{name} already exists')
    fs = SqliteDict(os.path.join(
                os.environ['HOME'],
                '.sqlitefs',
                f'{name}.db'), autocommit=True, tablename=volume_name)
    dopex = DOPE2(password.encode(), 8219, 32, 'GCM', b'',
                  block_size=512)
    fs['auth_key'] = dopex.serialize()
    dopex.fixate()
    fs[volume_name] = dopex.encode(init_fs(volume_name, fs_size=quota))
    fs.commit()
    fs.close()


@cli.command(short_help='Configure a Volume', help='Config Handler')
@click.argument('name', type=str)
@click.option('-m', '--mount', prompt='Mount Point',
              help='Specify Mountpoint Path', type=click.Path())
@click.option('-v', '--volume-name', help='Specify Volume Name', type=str,
              prompt='Volume Name', default=os.getlogin(), show_default=True)
@click.option('-d', '--debug',
              help='Enable Detail Debug(May Require Excess Space)',
              type=bool, default=False, prompt='Debug Mode', is_flag=True)
@click.option('-q', '--quota', help='Data Quota for the Volume in MB',
              type=float, default=1e3, prompt='Volume Size Quota',
              show_default=True)
@click.password_option()
def config(name, mount, volume_name, debug, quota, password):
    from configparser import ConfigParser
    config = ConfigParser()
    config.read(os.path.abspath(f'~/.sqlitefs/config.ini'))
    quota = int(quota * 1E6)
    fs = SqliteDict(os.path.join(
                os.environ['HOME'],
                '.sqlitefs',
                f'{name}.db'), autocommit=True,
                    tablename=config[name]['VOLUME_NAME'])
    try:
        dopex = DOPE2.marshall(fs['auth_key'], password.encode())
        dopex.fixate()
        DIR = load_fs(dopex.decode(fs[config[name]['VOLUME_NAME']]))
        if quota // 512 > DIR[0xF8]['f_blocks'] - DIR[0xF8]['f_bfree']:
            if DIR[0xF8]['f_bfree'] == DIR[0xF8]['f_blocks']:
                DIR[0xF8]['f_blocks'] = quota // 512
                DIR[0xF8]['f_files'] = quota // 4096
                DIR[0xF8]['f_bfree'] = quota // 512
                DIR[0xF8]['f_ffree'] = quota // 4096
                DIR[0xF8]['f_bavail'] = DIR[0xF8]['f_bfree']
                DIR[0xF8]['f_favail'] = DIR[0xF8]['f_ffree']
            else:
                used_blocks = DIR[0xF8]['f_blocks'] - DIR[0xF8]['f_bfree']
                used_files = DIR[0xF8]['f_files'] - DIR[0xF8]['f_ffree']
                DIR[0xF8]['f_bfree'] = quota // 512 - used_blocks
                DIR[0xF8]['f_ffree'] = quota // 4096 - used_files
                DIR[0xF8]['f_bavail'] = DIR[0xF8]['f_bfree']
                DIR[0xF8]['f_favail'] = DIR[0xF8]['f_ffree']
                DIR[0xF8]['f_blocks'] = quota // 512
                DIR[0xF8]['f_files'] = quota // 4096
        else:
            ValueError('Cannot Resize Volume')
        dopex.fixate()
        if config[name]['VOLUME_NAME'] != volume_name:
            fs[volume_name] = dopex.encode(dump_fs(DIR))
            del fs[config[name]['VOLUME_NAME']]
        else:
            fs[volume_name] = dopex.encode(dump_fs(DIR))
    except Exception as e:
        click.secho('ACCESS DENIED', fg='red')
        raise click.ClickException(e)
    config[name] = {
        'VOLUME_NAME': volume_name,
        'MOUNT': mount,
        'DEBUG': debug,
        'SIZE': quota * 1E-6
    }
    with open(os.path.abspath(f'~/.sqlitefs/config.ini'), 'w') as file:
        config.write(file)


def runtime_fusing(ctx):
    '''
    Runtime FUSE Server Integration Programme
    '''
    volume_name = ctx['CONFIG']['VOLUME_NAME']
    mount = ctx['CONFIG']['MOUNT']
    debug = ctx['CONFIG']['DEBUG']
    size = int(float(ctx['CONFIG']['SIZE'])*1E6)
    name = ctx['NAME']
    if not os.path.exists(mount):
        os.system(f'sudo mkdir {os.path.abspath(mount)} && '
                  + f'chown {os.getuid()}:{os.getgid()} '
                  + f'{os.path.abspath(mount)}')
    secfs = fuse.FUSE(SecFS(name, ctx['PASS'],
                            volume_name, size=size),
                      mountpoint=mount, foreground=True, fsname=name,
                      subtype='fuseblk')


@cli.group(short_help='Server Handler', help='SQLiteFS Server')
@click.argument('name')
@click.pass_context
def server(ctx, name):
    from configparser import ConfigParser
    click.echo('Loading Filesystem...', nl=False)
    ctx.ensure_object(dict)
    ctx.obj['NAME'] = name
    config = ConfigParser()
    config.read(os.path.abspath(f'~/.sqlitefs/config.ini'))
    try:
        ctx.obj['CONFIG'] = config[name]
    except KeyError:
        click.secho('FAILED', bg='bright_red')
        raise click.ClickException(f'No Filesystem named \'{name}\'')
    click.secho('OK', fg='green')


@server.command(short_help='Start File Server')
@click.option('--debug', type=bool, default=False, is_flag=True,
              help='Enable Debug Info')
@click.password_option()
@click.pass_context
def start(ctx, debug, password):
    ctx.obj['LOGGING'] = {'LOG': f"~/.sqlitefs/{ctx.obj['NAME']}.log"}
    ctx.obj['PASS'] = password.encode()
    runtime_fuse = partial(runtime_fusing, ctx=ctx.obj)
    try:
        daemon = Daemon(ctx.obj['NAME'], worker=runtime_fuse,
                        detach=(not debug),
                        pidfile=f"~/.sqlitefs/{ctx.obj['NAME']}.pid",
                        work_dir=os.environ['HOME'],
                        stdout_file=f"~/.sqlitefs/{ctx.obj['NAME']}.log",
                        stderr_file=f"~/.sqlitefs/{ctx.obj['NAME']}_error.log",
                        uid=os.getuid(), gid=os.getgid())
        daemon.do_action('start')
    except Exception as e:
        click.secho('FAILED', bg='bright_red')
        raise click.ClickException(e)


@server.command(short_help='Stop File Server')
@click.option('-f', '--force', default=False, is_flag=True)
@click.pass_context
def stop(ctx, force):
    runtime_fuse = partial(runtime_fusing, ctx=ctx.obj)
    try:
        daemon = Daemon(ctx.obj['NAME'],
                        pidfile=f"~/.sqlitefs/{ctx.obj['NAME']}.pid")
        os.system(f"umount {ctx.obj['NAME']}")
        daemon.stop(force=force)
    except Exception as e:
        click.secho('FAILED', bg='bright_red')
        raise click.ClickException(e)


@server.command(short_help='Restart File Server')
@click.option('--debug', type=bool, default=False, is_flag=True,
              help='Enable Debug Info')
@click.pass_context
def restart(ctx, debug):
    ctx.invoke(stop)
    ctx.invoke(start, debug=debug)


@server.command(short_help='File Server Status')
@click.option('-j', '--json', type=str, default=False,
              help='Get Status as JSON')
@click.pass_context
def status(ctx, json):
    runtime_fuse = partial(runtime_fusing, ctx=ctx.obj)
    try:
        daemon = Daemon(ctx.obj['NAME'],
                        pidfile=f"~/.sqlitefs/{ctx.obj['NAME']}.pid")
        daemon.status(json)
    except Exception as e:
        click.secho('FAILED', bg='bright_red')
        raise click.ClickException(e)


def main():
    cli(obj={})


if __name__ == '__main__':
    cli(obj={})
