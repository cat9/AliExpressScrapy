# -*- coding: utf-8 -*-
from scrapy import cmdline
import sys
import os

args = sys.argv
command = 'scrapy crawl aliexpress -s IMAGES_STORE=' + os.getcwd()+r'\tmp'
cmd = command.split()
if len(args) > 1:
    cmd = cmd+args[1:]
print(cmd)
cmdline.execute(cmd)
