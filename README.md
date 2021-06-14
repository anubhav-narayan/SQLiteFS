# SQLiteFS
[![Made with Python3](https://img.shields.io/badge/Made%20With-Python3-blue)](https://www.python.org/) [![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/anubhav-narayan/SQLiteFS/blob/master/LICENCE) [![Github version](https://img.shields.io/badge/version-0.11.0-green)
](http://github.com/anubhav-narayan/SQLiteFS) [![Github status](https://img.shields.io/badge/status-Public%20Beta-green)
](http://github.com/anubhav-narayan/SQLiteFS) [![Made with](https://img.shields.io/badge/Built%20with-SQLite3%20|%20Click%20|%20Daemonocle%20|%20PyCryptodome-blue)](http://github.com/anubhav-narayan/SQLiteFS)\
SQLite based Filesystem with DOPE Encryption
## Installation
### From source
To install from source use the following command, make sure you have `setuptools>=50.0.0`
```bash
python3 seutp.py install
```
### Via [Poetry](https://python-poetry.org)
```bash
poetry build
pip3 install dist/sqlitefs*.whl
```
NOTE : Currently only for Linux and Mac

## SQLiteFS CLI
```bash
$ sqlitefs
Usage: sqlitefs [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  config  Configure a Volume
  init    Create a New Volume
  server  Server Handler
```
INIT SQiteFS
```bash
$ sqlitefs init --help
Usage: sqlitefs init [OPTIONS] NAME

  Volume Creator

Options:
  -m, --mount PATH        Specify Mountpoint Path
  -v, --volume-name TEXT  Specify Volume Name  [default: sakae]
  -d, --debug             Enable Detail Debug(May Require Excess Space)
  -q, --quota FLOAT       Data Quota for the Volume in MB  [default: 1000.0]
  --password TEXT
  --help                  Show this message and exit.
```
CONFIG SQLiteFS
```bash
$ sqlitefs config --help
Usage: sqlitefs config [OPTIONS] NAME

  Config Handler

Options:
  -m, --mount PATH        Specify Mountpoint Path
  -v, --volume-name TEXT  Specify Volume Name  [default: sakae]
  -d, --debug             Enable Detail Debug(May Require Excess Space)
  -q, --quota FLOAT       Data Quota for the Volume in MB  [default: 1000.0]
  --password TEXT
  --help                  Show this message and exit
```
SQLiteFS Server
```bash
$ sqlitefs server --help
Usage: sqlitefs server [OPTIONS] NAME COMMAND [ARGS]...

  SQLiteFS Server

Options:
  --help  Show this message and exit.

Commands:
  restart  Restart File Server
  start    Start File Server
  status   File Server Status
  stop     Stop File Server

```
