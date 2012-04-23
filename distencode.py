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
    script = '''
ffmpeg -i %(src)s -f yuv4mpegpipe -pix_fmt yuv420p -vf "scale=%(width)d:%(height)d" - | ssh -C %(host)s "cat - > input.mpg && /usr/local/webm/bin/vpxenc input.mpg -o output.webm -p 2  -t 4  --good --cpu-used=0 --target-bitrate=%(bitrate)d --end-usage=vbr --auto-alt-ref=1 --fps=30000/1001 -v --minsection-pct=5 --maxsection-pct=800 --lag-in-frames=16 --kf-min-dist=0 --kf-max-dist=360 --token-parts=2 --static-thresh=0 --drop-frame=0 --min-q=0 --max-q=60 && cat output.webm && rm -f input.mpg output.webm" > interm.%(cookie)s.webm && ffmpeg -i interm.%(cookie)s.webm -i %(src)s -vcodec copy -acodec libvorbis -aq 4 -map 0:v -map 1:a -y %(dest)s && rm -f interm.%(cookie)s.webm
'''

    def __init__(self, src, bitrate, width, height, host):
        self.src = src
        self.bitrate = bitrate
        self.width = width
        self.height = height
        self.dest = re.sub(u'(mp4|f4v|m4v)$', u'webm', self.src)
        self.host = host
        self.cookie = hashlib.md5(str(random.getrandbits(256))).hexdigest()

    def encode(self):
        print self.script % self.__dict__
        with open('%s.log' % self.dest, 'w') as f:
            subprocess.check_call(self.script % self.__dict__, shell=True, stderr=f)

if __name__ == '__main__':
    import sys
    import os
    pool = HostPool(os.environ['DISTENCODE_HOSTS'].split(':'))
    host = None
    try:
        host = pool.acquire()
        Encoder(src=sys.argv[1], bitrate=int(sys.argv[2]), width=int(sys.argv[3]), height=int(sys.argv[4]), host=host).encode()
    finally:
        if host is not None:
            pool.release(host)
