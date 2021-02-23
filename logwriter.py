# -*- coding: utf-8 -*-
# @Explain  : 
# @Time     : 2021/02/22 11:31 
# @Author   : tide
# @FileName : logwriter

import sys
import traceback


def trace_full():
    exc_info = sys.exc_info()
    stack = traceback.extract_stack()
    tb = traceback.extract_tb(exc_info[2])
    full_tb = stack[:-1] + tb
    exc_line = traceback.format_exception_only(*exc_info[:2])
    return "Traceback (most recent call last):\n{}\n{}".format(
        "".join(traceback.format_list(full_tb)),
        "".join(exc_line)
    )
