# -*- coding: utf-8 -*-
from scrapy import cmdline
import sys

args = sys.argv
cmd = "scrapy crawl aliexpress".split()
if len(args) > 1:
    cmd = cmd+args[1:]
print(cmd)
cmdline.execute(cmd)
