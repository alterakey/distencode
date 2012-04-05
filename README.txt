README
========

Copyright (C) 2012 Takahiro Yoshimura <altakey@gmail.com>
All rights reserved.

This is distencode, an encoder could distribute workload on a
homogenous cluster built for the WebM encoding.

0. HOW TO USE
===============

Makefile:
--------------------------------------
encoder:=python distencode.py

all: movie1.webm movie2.webm ...

movie1.webm: movie1.mov
	$(encoder) $< 2000 1280 720

movie2.webm: movie2.mov
	$(encoder) $< 2000 1280 720

...
--------------------------------------

$ DISTENCODE_HOSTS='localhost:red:green:blue:yellow:black' make -j8 all
