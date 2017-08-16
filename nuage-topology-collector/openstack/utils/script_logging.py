#  Copyright 2017 NOKIA
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import collections
import contextlib
import functools
import logging
import os
import sys
import time


USER_LOGGING_LEVEL = logging.INFO + 1
CONSOLE_FORMAT = '%(spaces)s%%(message)s'
FILE_FORMAT = '%%(asctime)s %%(levelname)s %(spaces)s%%(message)s'
LOG = None

log_file = ""
indentations = 0
console_formatter = None
file_formatter = None


class SingleLevelFilter(logging.Filter):
    def __init__(self, passlevel):
        super(SingleLevelFilter, self).__init__()
        self.passlevel = passlevel

    def filter(self, record):
        return record.levelno == self.passlevel


def init_logging(name):
    global log_file, console_formatter, file_formatter, LOG
    log_dir = os.path.expanduser('~') + '/nuage_logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    console_formatter = logging.Formatter()
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(console_formatter)
    stdout.setLevel(USER_LOGGING_LEVEL)
    stdout.addFilter(SingleLevelFilter(USER_LOGGING_LEVEL))
    root_logger.addHandler(stdout)

    def user(self, message, *args, **kws):
        exc_info = kws.pop('exc_info', False)
        message = message.replace('\n', '\n%s' % (indentations * '  '))
        args = tuple([arg.replace('\n', '\n%s' % (indentations * '  '))
                      for arg in args])
        kws = {k: v.replace('\n', '\n%s' % (indentations * '  '))
               for k, v in kws}
        if self.isEnabledFor(USER_LOGGING_LEVEL):
            self._log(USER_LOGGING_LEVEL, message, args, **kws)
        if exc_info:
            self._log(logging.ERROR, "", [], exc_info=True, **kws)

    logging.addLevelName(USER_LOGGING_LEVEL, "USER")
    logging.Logger.user = user

    file_formatter = logging.Formatter()
    log_file = log_dir + '/%s_%s.log' % (
        name, time.strftime("%d-%m-%Y_%H:%M:%S"))
    hdlr = logging.FileHandler(log_file)
    hdlr.setFormatter(file_formatter)
    hdlr.setLevel(logging.NOTSET)
    root_logger.addHandler(hdlr)

    _update_formatters()
    root_logger.user("Logfile created at %s" % log_file)
    LOG = logging.getLogger()


def _update_formatters():
    global console_formatter, file_formatter
    console_formatter._fmt = CONSOLE_FORMAT % {'spaces': indentations * '  '}
    file_formatter._fmt = FILE_FORMAT % {'spaces': indentations * '  '}


def _update_indentation(delta):
    global indentations
    indentations += delta
    _update_formatters()


def indent():
    _update_indentation(1)


def unindent():
    _update_indentation(-1)


def step(description=None):
    """Decorator for indenting all logging for the duration of the method.

    :param description: if present, will log "start <description>" and end.
    :return: decorated function
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            exception = False
            try:
                if description is not None:
                    LOG.user('Start %s' % description)
                indent()
                return fn(*args, **kwargs)
            except BaseException:
                exception = True
                raise
            finally:
                unindent()
                if description is not None and not exception:
                    LOG.user('Finished %s\n' % description)
        return wrapped
    return decorator


@contextlib.contextmanager
def indentation():
    """contextmanager to indent logging for the duration of the context.

    Usage:
    with indentation():
        # code where logging will be indented 1 level
    """
    try:
        indent()
        yield
    finally:
        unindent()


def iterate(iterable, resource_name_plural,
            message='%(total)s%(resource_name_plural)s remaining',
            newline=False):
    """helper method for loops to provide automatic progress logging.

    At the start of the loop it will print
    | Start <message>
    At the end of the loop it will print
    | Finished <message>
    Advised not to use when you may 'break' the loop early or return in it. The
    estimted time logging would be pointless as well as the 'Finished' message
    will not print.
    Any logging happening inside the loop will be automatically indented.
    Every 5 seconds a message will print on the console indicating the progress
    in the loop. Assuming not a stream was passed or certain generator without
    length available. It will print:
    | <time in loop> <message> (<percentage complete>, <estimated time left>)
    When a stream was passed as parameter, it will just print
    | <total time in loop> <msg>
    Usage:
    for port in nuage_logging.iterate(ports, "ports"):
        # code
    """
    msg_args = {}
    try:
        total = len(iterable)
        msg_args['total'] = str(total) + ' '
    except TypeError:
        # Streams or some generators won't have len property.
        total = None
        msg_args['total'] = ''
        message = 'processing %(total)s%(resource_name_plural)s'
    msg_args['resource_name_plural'] = resource_name_plural

    main_message = message[0].lower() + message[1:]
    main_message %= msg_args

    last_log_index = -1
    start = time.time()
    last_log_time = start
    time_history = collections.deque(maxlen=5)

    LOG.user("Start processing %(total)s%(resource_name_plural)s" % msg_args)
    try:
        with indentation():
            for i, x in enumerate(iterable):
                yield x
                now = time.time()
                seconds_passed = now - last_log_time
                if (seconds_passed > 5 or i == 0) and i + 1 != total:
                    _log_iter_progress(i + 1, total, resource_name_plural,
                                       message, start, now, seconds_passed,
                                       i - last_log_index, time_history)
                    last_log_time = now
                    last_log_index = i
    except Exception:
        raise
    else:
        LOG.user("Finished processing %(total)s%(resource_name_plural)s"
                 % msg_args + ('\n' if newline else ''))


def _log_iter_progress(i, total, resource_name_plural, message, start, now,
                       seconds_passed, processed_items, time_history):
    message = "%(time_taken)s | " + message
    total_seconds_taken = now - start
    msg_args = {'resource_name_plural': resource_name_plural,
                'time_taken': _seconds_to_hms_str(total_seconds_taken),
                'total': str(total - i) + ' ' if total is not None else ''}

    if total is None:
        LOG.user(message % msg_args + ' (unknown time left)')
    else:
        percent_complete = int(round(100.0 * i / total))

        seconds_per_item = float(seconds_passed) / processed_items
        time_history.append(seconds_per_item)
        avg_time_per_item = sum(time_history) / len(time_history)
        seconds_left = avg_time_per_item * (total - i)

        message += " (%(percentage)s%%, time left: ~%(time_left)s)"
        msg_args['percentage'] = percent_complete
        msg_args['time_left'] = _seconds_to_hms_str(seconds_left)

        LOG.user(message % msg_args)


def _seconds_to_hms_str(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%02d:%02d:%02d" % (h, m, s)
