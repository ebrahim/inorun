#!/usr/bin/python
# vim: set fileencoding=utf-8 ts=2 sw=2 expandtab :

import os,sys,resource
from optparse import OptionParser
from syslog import *
from pyinotify import *

__author__ = "Benedikt Böhm"
__copyright__ = "Copyright (C) 2007 Benedikt Böhm"
__version__ = "0.1"

class RsyncEvent(ProcessEvent):
  options = None

  def __init__(self, options):
    self.options = options

  def sync(self):
    args = [self.options.rsync_path, "-ltrp", "--delete"]
    if self.options.verbose:
      args.append("-v")
    if self.options.exclude:
      args.append("--exclude-from=%s" % self.options.exclude)
    args.append(self.options.dir)
    args.append("%s")
    cmd = " ".join(args)
    for remote in self.options.remotes:
      if self.options.pretend:
        syslog("would execute `%s'" % (cmd % remote))
      else:
        syslog(LOG_DEBUG, "executing %s" % (cmd % remote))
        proc = os.popen(cmd % remote)
        for line in proc:
          syslog(LOG_DEBUG, "[rsync] %s" % line.strip())

  def process_default(self, event):
    syslog(LOG_DEBUG, "caught %s on %s" % \
        (event.event_name, os.path.join(event.path, event.name)))
    if not event.event_name in self.options.events:
      syslog(LOG_DEBUG, "ignoring %s on %s" % \
          (event.event_name, os.path.join(event.path, event.name)))
      return
    self.sync()

def daemonize():
  try:
    pid = os.fork()
  except OSError, e:
    raise Exception, "%s [%d]" % (e.strerror, e.errno)

  if (pid == 0):
    os.setsid()
    try:
      pid = os.fork()
    except OSError, e:
      raise Exception, "%s [%d]" % (e.strerror, e.errno)
    if (pid == 0):
      os.chdir('/')
      os.umask(0)
    else:
      os._exit(0)
  else:
    os._exit(0)

  os.open("/dev/null", os.O_RDWR)
  os.dup2(0, 1)
  os.dup2(0, 2)

  return 0

def parse_options():
  usage = "usage: %prog [options]"
  parser = OptionParser(usage, version = __version__)

  parser.add_option(
      "-d", "--daemon",
      action = "store_true",
      dest = "daemonize", default = False,
      help = "daemonize %prog")
  parser.add_option(
      "-e", "--exclude-from",
      dest = "exclude",
      metavar = "FILE",
      help = "exclude directories listed in FILE")
  parser.add_option(
      "-m", "--mask",
      action = "append",
      dest = "events",
      metavar = "EVENT",
      help = "synchronize on inotify event EVENT")
  parser.add_option(
      "-p", "--pretend",
      action = "store_true",
      dest = "pretend", default = False,
      help = "do not actually call rsync")
  parser.add_option(
      "-r", "--remote",
      action = "append",
      dest = "remotes",
      metavar = "DEST",
      help = "synchronize to (rsync-compatible) DEST")
  parser.add_option(
      "--rsync-path",
      default = "/usr/bin/rsync",
      metavar = "PATH",
      help = "PATH to the rsync binary")
  parser.add_option(
      "-v", "--verbose",
      action = "store_true",
      dest = "verbose", default = False,
      help = "print debugging information")
  parser.add_option(
      "-w", "--watch",
      dest = "dir",
      metavar = "DIR",
      help = "watch DIR for changes")

  (options, args) = parser.parse_args()

  if len(args) > 0:
    parser.error("too many arguments")

  if options.dir == None:
    parser.error("no watch directory given")
  if not os.path.isdir(options.dir):
    parser.error("directory does not exist: %s" % options.dir)
  if not os.path.isabs(options.dir):
    options.dir = os.path.abspath(options.dir)

  if options.remotes == None:
    parser.error("no remote location(s) specified")

  if options.exclude and not os.path.isfile(options.exclude):
    parser.error("exclude file does not exist: %s" % options.exclude)
  if options.exclude and not os.path.isabs(options.exclude):
    options.exclude = os.path.abspath(options.exclude)

  if not os.path.isabs(options.rsync_path):
    parser.error("rsync path needs to be absolute")

  all_events = [
      "IN_ACCESS",
      "IN_ATTRIB",
      "IN_CLOSE_WRITE",
      "IN_CLOSE_NOWRITE",
      "IN_CREATE",
      "IN_DELETE",
      "IN_DELETE_SELF",
      "IN_MODIFY",
      "IN_MOVED_FROM",
      "IN_MOVED_TO",
      "IN_OPEN"
  ]

  default_events = [
      "IN_CLOSE_WRITE",
      "IN_CREATE",
      "IN_DELETE",
      "IN_MOVED_FROM",
      "IN_MOVED_TO"
  ]

  if not options.events:
    options.events = default_events
  for event in options.events:
    if not event in all_events:
      parser.error("invalid inotify event: %s" % event)

  return options

def main():
  options = parse_options()

  logopt = LOG_PID|LOG_CONS
  if not options.daemonize:
    logopt |= LOG_PERROR
  openlog("inosync", logopt, LOG_DAEMON)
  if options.verbose:
    setlogmask(LOG_UPTO(LOG_DEBUG))
  else:
    setlogmask(LOG_UPTO(LOG_INFO))

  syslog(LOG_DEBUG, "event mask is %s" % options.events)

  if options.daemonize:
    daemonize()

  wm = WatchManager()
  ev = RsyncEvent(options)
  notifier = Notifier(wm, ev)
  wds = wm.add_watch(options.dir, EventsCodes.ALL_EVENTS,
      rec = True, auto_add = True)

  syslog(LOG_DEBUG, "starting initial synchronization on %s" % options.dir)
  ev.sync()
  syslog(LOG_DEBUG, "initial synchronization on %s done" % options.dir)

  syslog("resuming normal operations on %s" % options.dir)
  while True:
    try:
      notifier.process_events()
      if notifier.check_events():
        notifier.read_events()
    except KeyboardInterrupt:
      notifier.stop()
      break

  sys.exit(0)

if __name__ == "__main__":
  main()
