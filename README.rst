=======
inorun
=======

:Authors: - `Benedikt Böhm <bb@xnull.de>`
          - `Ebrahim Mohammadi <ebrahim@mohammadi.ir>`
:Version: 0.1.0
:Web: http://code.ebrahim.ir/inorun
:Mercurial: ``hg clone http://bitbucket.org/ebrahim/inorun``
:Git: ``git clone https://github.com/ebrahim/inorun.git``
:Download: http://code.ebrahim.ir/inorun/downloads

Rationale
=========

Wanna run some command on some file system event? inorun is for you!

The inorun daemon leverages the inotify service available in recent linux
kernels to monitor file system events and run your desired command on them.


Usage
=====

inorun calls your desired commands on your desired events with three arguments:

1. Remote address
2. Watched path
3. Relative path to the file under watched path on which the event has occurred

inorun comes with an init script named inorun which runs an inorun daemon using
the default config file located at ``/etc/inorun/default.py``.

::

  inorun [OPTIONS]

    -c FILE     load configuration from FILE
    -d          daemonize (fork to background)
    -p          do not actually call rrun
    -v          print debugging information
    --version   show program's version number and exit
    -h, --help  show this help message and exit


Configuration
=============

Remeber to increase maximum allowed user watched if you're going to watch huge
directory trees:

::

    # sysctl -w fs.inotify.max_user_watches=262144


This is an example config file for syncing an Ubuntu repository to 10.0.0.2:

::

    # directory that should be watched for changes
    wpath = "/repo/ubuntu"

    rnodes = [ "10.0.0.2" ]

    # event mask (only sync on these events)
    emask = {
        "IN_CLOSE_WRITE": "/usr/local/bin/sync-copy",
        "IN_CREATE":      "/usr/local/bin/sync-copy",
        "IN_MOVED_TO":    "/usr/local/bin/sync-copy",
        "IN_DELETE":      "/usr/local/bin/sync-remove",
        "IN_MOVED_FROM":  "/usr/local/bin/sync-remove",
    }

    # event delay in seconds (prevents huge amounts of syncs, but dicreases the
    # realtime side of things)
    # Default: 1
    edelay = 10

    # initial event to raise virtually on watched directory, maybe to start an
    # initial full copy
    #initevent = "IN_CREATE"


Bugs
====

inorun has many bugs, none of which I know at the moment. Report them please.

Requirements
============

To use this script you need the following software installed on your system:

- linux-2.6.13 or later
- Python-2.5 or later
- pyinotify-0.8.7 or later


Related Software
================

inorun is based on `inosync <https://github.com/hollow/inosync>`_.
