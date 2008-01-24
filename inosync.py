#!/usr/bin/python
# vim: set fileencoding=utf-8 ts=2 sw=2 expandtab :
#
# Copyright (c) 2007-2008 Benedikt Böhm
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The name of the author may not be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ChangeLog:
#
# *inosync-0.2 (24 Jan 2008):
#   use configuration files
#   add event delay option
#
# *inosync-0.1 (09 Jan 2008):
#   initial version

import os,sys
from optparse import OptionParser,make_option
from time import sleep
from syslog import *
from pyinotify import *

__author__ = "Benedikt Böhm"
__copyright__ = "Copyright (c) 2007-2008 Benedikt Böhm"
__version__ = 0,2

OPTION_LIST = [
  make_option(
      "-c", dest = "config",
      default = "/etc/inosync/default.py",
      metavar = "FILE",
      help = "load configuration from FILE"),
  make_option(
      "-d", dest = "daemonize",
      action = "store_true",
      default = False,
      help = "daemonize %prog"),
  make_option(
      "-p", dest = "pretend",
      action = "store_true",
      default = False,
      help = "do not actually call rsync"),
  make_option(
      "-v", dest = "verbose",
      action = "store_true",
      default = False,
      help = "print debugging information"),
]

ALL_EVENTS = [
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

DEFAULT_EVENTS = [
    "IN_CLOSE_WRITE",
    "IN_CREATE",
    "IN_DELETE",
    "IN_MOVED_FROM",
    "IN_MOVED_TO"
]

class RsyncEvent(ProcessEvent):
  pretend = None
  dirty = True

  def __init__(self, pretend=False):
    self.pretend = pretend

  def sync(self):
    if not self.dirty:
      return
    args = [config.rsync, "-ltrp", "--delete"]
    args.append("--bwlimit=%s" % config.rspeed)
    if "excludes" in dir(config):
      for exclude in config.excludes:
        args.append("--exclude=%s" % exclude)
    args.append(config.wpath)
    args.append("%s")
    cmd = " ".join(args)
    for node in config.rnodes:
      if self.pretend:
        syslog("would execute `%s'" % (cmd % node))
      else:
        syslog(LOG_DEBUG, "executing %s" % (cmd % node))
        proc = os.popen(cmd % node)
        for line in proc:
          syslog(LOG_DEBUG, "[rsync] %s" % line.strip())
    self.dirty = False

  def process_default(self, event):
    syslog(LOG_DEBUG, "caught %s on %s" % \
        (event.event_name, os.path.join(event.path, event.name)))
    if not event.event_name in config.emask:
      syslog(LOG_DEBUG, "ignoring %s on %s" % \
          (event.event_name, os.path.join(event.path, event.name)))
      return
    self.dirty = True

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

def load_config(filename):
  if not os.path.isfile(filename):
    raise RuntimeError, "configuration file does not exist: %s" % filename

  configdir  = os.path.dirname(filename)
  configfile = os.path.basename(filename)

  if configfile.endswith(".py"):
    configfile = configfile[0:-3]

  sys.path.append(configdir)
  exec("import %s as __config__" % configfile)
  sys.path.remove(configdir)

  global config
  config = __config__

  if not "wpath" in dir(config):
    raise RuntimeError, "no watch path given"
  if not os.path.isdir(config.wpath):
    raise RuntimeError, "watch path does not exist: %s" % config.wpath
  if not os.path.isabs(config.wpath):
    config.wpath = os.path.abspath(config.wpath)

  if not "rnodes" in dir(config) or len(config.rnodes) < 1:
    raise RuntimeError, "no remote nodes given"

  if not "rspeed" in dir(config) or config.rspeed < 0:
    config.rspeed = 0

  if not "emask" in dir(config):
    config.emask = DEFAULT_EVENTS
  for event in config.emask:
    if not event in ALL_EVENTS:
      raise RuntimeError, "invalid inotify event: %s" % event

  if not "edelay" in dir(config):
    config.edelay = 10
  if config.edelay < 1:
    raise RuntimeError, "event delay needs to be greater than 1"

  if not "rsync" in dir(config):
    config.rsync = "/usr/bin/rsync"
  if not os.path.isabs(config.rsync):
    raise RuntimeError, "rsync path needs to be absolute"
  if not os.path.isfile(config.rsync):
    raise RuntimeError, "rsync binary does not exist: %s" % config.rsync

def main():
  version = ".".join(map(str, __version__))
  parser = OptionParser(option_list=OPTION_LIST,version="%prog " + version)
  (options, args) = parser.parse_args()

  if len(args) > 0:
    parser.error("too many arguments")

  logopt = LOG_PID|LOG_CONS
  if not options.daemonize:
    logopt |= LOG_PERROR
  openlog("inosync", logopt, LOG_DAEMON)
  if options.verbose:
    setlogmask(LOG_UPTO(LOG_DEBUG))
  else:
    setlogmask(LOG_UPTO(LOG_INFO))

  load_config(options.config)

  if options.daemonize:
    daemonize()

  wm = WatchManager()
  ev = RsyncEvent(options.pretend)
  notifier = Notifier(wm, ev)
  wds = wm.add_watch(config.wpath, EventsCodes.ALL_EVENTS,
      rec = True, auto_add = True)

  syslog(LOG_DEBUG, "starting initial synchronization on %s" % config.wpath)
  ev.sync()
  syslog(LOG_DEBUG, "initial synchronization on %s done" % config.wpath)

  syslog("resuming normal operations on %s" % config.wpath)
  while True:
    try:
      notifier.process_events()
      if notifier.check_events(0):
        notifier.read_events()
      ev.sync()
      sleep(config.edelay)
    except KeyboardInterrupt:
      notifier.stop()
      break

  sys.exit(0)

if __name__ == "__main__":
  main()
