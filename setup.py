from setuptools import setup, find_packages
setup(
    name='SQLiteFS',
    version='0.11.0',
    description="SQLite based Filesystem with DOPE Encryption",
    author='Anubhav Mattoo',
    author_email='anubhavmattoo@outlook.com',
    pakages=find_packages(),
    install_requires=[
        'pycryptodome>=3.9',
        'dill',
        'bchlib',
        'sqlitedict'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Security :: Cryptography',
        'Topic :: System :: Filesystems'
    ]
)
