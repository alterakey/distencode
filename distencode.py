# distencode: Distributed WebM encoder
# Copyright (C) 2012 Takahiro Yoshimura <altakey@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import subprocess
import hashlib
import random
import lockfile

class HostPool(object):
    lock = None

    def __init__(self, hosts):
        self.hosts = hosts

    def filelock(self, host):
        return lockfile.FileLock('distencode.scratch.%s' % hashlib.md5(host).hexdigest())

    def acquire(self):
        while True:
            for host in self.hosts:
                lock = self.filelock(host)
                try:
                    lock.acquire(timeout=3)
                    return host
                except lockfile.LockTimeout:
                    pass


    def release(self, host):
        lock = self.filelock(host)
        lock.release()

class Encoder(object):
    def __init__(self, src, dest, bitrate, width, height, host):
        self.src = src
        self.bitrate = bitrate
        self.width = width
        self.height = height
        self.dest = dest
        self.host = host
        self.cookie = hashlib.md5(str(random.getrandbits(256))).hexdigest()

    def encode(self):
        script = self.get_script()
        print script % self.__dict__
        with open('%s.log' % self.dest, 'w') as f:
            subprocess.check_call(script % self.__dict__, shell=True, stderr=f)

    def get_script(self):
        if self.host == 'localhost':
            return self.script_localhost
        else:
            return self.script

class WebMEncoder(Encoder):
    script = '''
prep "%(src)s" %(width)d %(height)d | ssh -C %(host)s "webm %(cookie)s - %(bitrate)d %(width)d %(height)d" > "%(dest)s"
'''

    script_localhost = '''
prep "%(src)s" %(width)d %(height)d | webm %(cookie)s - %(bitrate)d %(width)d %(height)d > "%(dest)s"
'''

class H264Encoder(Encoder):
    script = '''
prep "%(src)s" %(width)d %(height)d | ssh -C %(host)s "h264 %(cookie)s - %(bitrate)d %(width)d %(height)d" > "%(dest)s"
'''

    script_localhost = '''
prep "%(src)s" %(width)d %(height)d | h264 %(cookie)s - %(bitrate)d %(width)d %(height)d > "%(dest)s"
'''

    def __init__(self, src, dest, bitrate, width, height, host):
        super(H264Encoder, self).__init__(src, dest, bitrate, width, height, host)
        self.bitrate = self.bitrate * 1000

if __name__ == '__main__':
    import sys
    import os
    pool = HostPool(os.environ['DISTENCODE_HOSTS'].split(':'))
    host = None
    try:
        host = pool.acquire()
        format = sys.argv[1]
        encoder = {'h264':H264Encoder, 'webm':WebMEncoder}
        encoder(src=sys.argv[2], dest=sys.argv[3], bitrate=int(sys.argv[4]), width=int(sys.argv[5]), height=int(sys.argv[6]), host=host).encode()
    finally:
        if host is not None:
            pool.release(host)
