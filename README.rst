=======
inosync
=======

:Author: `Benedikt Böhm <bb@xnull.de>`_
:Version: 0.2.1
:Web: http://bb.xnull.de/projects/inosync/
:Source: http://git.xnull.de/gitweb/?p=inosync.git (also on `github <http://github.com/hollow/inosync>`_)
:Download: http://bb.xnull.de/projects/inosync/dist/

Rationale
=========

System administrators have relied on cron+rsync for years to constantly
synchronize files and directories to remote machines. However, this technique
has a huge disadvantage for content distribution with near real-time
requirements, e.g. podcasts and blogging.

It is not feasible to let authors wait for their content to get synchronized
every x hours with regard to the enormous pace of articles and
podcasts nowadays.

The inosync daemon leverages the inotify service available in recent linux
kernels to monitor and synchronize changes within directories to remote nodes.


Usage
=====

::

  inosync [OPTIONS]

    -c FILE     load configuration from FILE
    -d          daemonize (fork to background)
    -p          do not actually call rsync
    -v          print debugging information
    --version   show program's version number and exit
    -h, --help  show this help message and exit


Configuration
=============

Configuration files are simple python scripts, merely declaring necessary
variables. Below is an example configuration to synchronize ``/var/www``
except ``/var/www/localhost`` to 3 remote locations:
::

  # directory that should be watched for changes
  wpath = "/var/www/"

  # exclude list for rsync
  rexcludes = [
  	"/localhost",
  ]

  # common remote path
  rpath = "/var/www/"

  # remote locations in rsync syntax
  rnodes = [
  	"a.mirror.com:" + rpath,
  	"b.mirror.com:" + rpath,
  	"c.mirror.com:" + rpath,
  ]

  # limit remote sync speed (in KB/s, 0 = no limit)
  #rspeed = 0

  # event mask (only sync on these events)
  #emask = [
  #	"IN_CLOSE_WRITE",
  #	"IN_CREATE",
  #	"IN_DELETE",
  #	"IN_MOVED_FROM",
  #	"IN_MOVED_TO",
  #]

  # event delay in seconds (this prevents huge
  # amounts of syncs, but dicreases the 
  # realtime side of things)
  #edelay = 10

  # rsync binary path
  #rsync = "/usr/bin/rsync"


Bugs
====

There are no known bugs currently, however, due to the design of inosync, there
are several shortcomings:

- inosync cannot parse rsync excludes and therefore calls rsync on changes in
  excluded directories as well. (`of course rsync still excludes these
  directories`)
- It is easily possible to flood the daemon with huge amounts of change events,
  potentially resulting in enormous bandwidth and connection usage.

Requirements
============

To use this script you need the following software installed on your system:

- linux-2.6.13 or later
- Python-2.4 or later
- pyinotify-0.7.0 or later


Related Software
================

inosync is similar to `lsyncd <http://www.pri.univie.ac.at/index.php?c=show&CEWebS_what=Lsyncd>`_,
but uses a lot less (nasty) magic to parse rsync excludes and shared www
directories. Additionally inosync has no limitation on filename size and number
of active watchpoints.

A comparision to other approaches like DRBD, incron and FUSE can be found at
lsyncds project page, mentioned above.
