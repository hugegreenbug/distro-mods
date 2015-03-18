#!/usr/bin/env python
"""
SessionManager
Copyright (c) 2010--2011, Olivier Mehani <shtrom@ssji.net>
All rights reserved.

$Id$
A drop-in replacement for org.gnome.SessionManager, doing almost nothing.
Loosely based on basic instructions at [0,1,2,3,5,6].

[0] http://people.gnome.org/~mccann/gnome-session/docs/gnome-session.html
[1] http://www.amk.ca/diary/2007/04/rough_notes_python_and_dbus.html
[2] http://paste.lisp.org/display/45824
[3] http://www.lamalex.net/2010/03/help-does-anyone-know-how-to-export-properties-with-python-dbus/
[4] http://thp.io/2007/09/x11-idle-time-and-focused-window-in.html
[5] http://www.eurion.net/python-snippets/snippet/GConf%3A%20get_set%20values.html
[6] http://lists.gnupg.org/pipermail/gnupg-users/2006-March/028189.html

---
Add Inhibit method at [7]
[7] https://people.gnome.org/~mccann/gnome-session/docs/gnome-session.html#org.gnome.SessionManager.Inhibit

Original Authors Page
http://www.narf.ssji.net/~shtrom/wiki/projets/gnomescreensavernosession

---

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.
3. Neither the name of Olivier Mehani nor the names of its contributors
may be used to endorse or promote products derived from this software
without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

"""

__version__ = "$Revision$"


import dbus
import dbus.service
import dbus.glib
import gobject

import gtk

import ctypes
import os

import signal


ogSM	= 'org.gnome.SessionManager'
ogSMp	= '/org/gnome/SessionManager'
ogSMP	= 'org.gnome.SessionManager.Presence'
ogSMPp	= '/org/gnome/SessionManager/Presence'

class SessionManager(dbus.service.Object):
    inhibit_cookie = 0xdeadbeef

    def __init__(self):
        bus_name = dbus.service.BusName(ogSM,
            bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name,
            ogSMp)
        self.presence = SessionManagerPresence()
        #print "%s emulation ready" % ogSM

    def get_smp(self):
        return self.presence

    @dbus.service.method(dbus_interface=ogSM,
                         in_signature='susu', out_signature='u')
    def Inhibit(self, app_id, toplevel_xid, reason, flags):
        return self.inhibit_cookie

class SessionManagerPresence(dbus.service.Object):
    PRESENCE_AVAILABLE  = 0
    PRESENCE_INVISIBLE  = 1
    PRESENCE_BUSY		= 2
    PRESENCE_IDLE		= 3

    status			= PRESENCE_AVAILABLE
    status_text		= ""

    def __init__(self):
        bus_name = dbus.service.BusName(ogSMP,
            bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name,
            ogSMPp)
        #print "%s emulation ready" % ogSMP

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
        in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        #print "%s.GetAll(%s)" % (ogSMP, interface_name)
        return {'status':		dbus.UInt32(self.status),
            'status-text':  self.status_text,
            }
    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
        in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        #print "%s.Get(%s, %s)" % (ogSMP, interface_name, property_name)
        #print " -> %s" % str(self.GetAll(interface_name)[property_name])
        return self.GetAll(interface_name)[property_name]
    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
        in_signature='ssv')
    def Set(self, interface_name, property_name, value):
        #print "%s.Set(%s, %s, %s)" % \
        #	(ogSMP, interface_name, property_name, value)
        pass

    @dbus.service.method(dbus_interface=ogSMP, in_signature='u')
    def SetStatus(self, status):
        self.status = status

    @dbus.service.method(dbus_interface=ogSMP, in_signature='u')
    def SetStatusText(self, status_text):
        self.status_text = status_text

    @dbus.service.signal(dbus_interface=ogSMP, signature='u')
    def StatusChanged(self, status):
        self.SetStatus(status)

    @dbus.service.signal(dbus_interface=ogSMP, signature='s')
    def StatusTextChanged(self, status_text):
        self.SetStatusText(status_text)


class XScreenSaverIdleChecker():
    class XScreenSaverInfo(ctypes.Structure):
        """ typedef struct { ... } XScreenSaverInfo; """
        _fields_ = [('window',	  ctypes.c_ulong), # screen saver window
            ('state',	   ctypes.c_int),   # off,on,disabled
            ('kind',		ctypes.c_int),   # blanked,internal,external
            ('since',	   ctypes.c_ulong), # milliseconds
            ('idle',		ctypes.c_ulong), # milliseconds
            ('event_mask',  ctypes.c_ulong)] # events

    def __init__(self, idle_timeout):
        self.idle_timeout = idle_timeout
        self.idle	= False
        self.xlib	= ctypes.cdll.LoadLibrary('libX11.so.6')
        self.dpy	= self.xlib.XOpenDisplay(os.environ['DISPLAY'])
        self.root	= self.xlib.XDefaultRootWindow(self.dpy)
        self.xss	= ctypes.cdll.LoadLibrary('libXss.so.1')
        self.xss.XScreenSaverAllocInfo.restype \
                = ctypes.POINTER(self.XScreenSaverInfo)
        print ("XScreenSaverIdleChecker ready with timeout %d" % idle_timeout)

    def check_idle(self, smp):
        #print "Checking idleness..."
        xss_info = self.xss.XScreenSaverAllocInfo()
        self.xss.XScreenSaverQueryInfo(self.dpy, self.root, xss_info)
        idle = xss_info.contents.idle/1000

        if idle >= self.idle_timeout:
            if not self.idle:
#                print "Becoming idle"
                self.idle = True
#                self.forget_gpg_passphrases()
                smp.StatusChanged(smp.PRESENCE_IDLE)
        else:
            if self.idle:
#                print "Not idle anymore"
                self.idle = False
                smp.StatusChanged(smp.PRESENCE_AVAILABLE)

        gobject.timeout_add(100, self.check_idle, smp)

    def forget_gpg_passphrases(self):
        if os.environ.has_key("GPG_AGENT_INFO"):
            gpg_agent_pid = int(os.environ['GPG_AGENT_INFO'].split(":")[1])
            try:
                os.kill(gpg_agent_pid, signal.SIGHUP)
            except Exception, e:
                print "Can't forget GPG passphrase: %s" % e


from subprocess import Popen, PIPE 
output = Popen(["gsettings", "get", "org.gnome.desktop.session", "idle-delay"], stdout=PIPE).communicate()[0]
output = output.split(" ")
if output is not None and output[1] is not None:
    idle_delay = int(output[1])
else:
    # 5 minutes
    idle_delay = 300

sessmgr = SessionManager()

xssic = XScreenSaverIdleChecker(idle_delay)
xssic.check_idle(sessmgr.get_smp())

gtk.main()
