from glob import glob
import inspect
import os.path
import re
import sys
import unittest

import _pydevd_bundle.pydevd_comm as _pydevd

import ptvsd
from pydevd import _commands
#_commands.import_command_ids(vars())
from pydevd._commands import (
    CMD_ADD_DJANGO_EXCEPTION_BREAK,
    #CMD_ADD_EXCEPTION_BREAK,
    #CMD_CHANGE_VARIABLE,
    CMD_CONSOLE_EXEC,
    CMD_ENABLE_DONT_TRACE,
    #CMD_ERROR,
    CMD_EVALUATE_CONSOLE_EXPRESSION,
    CMD_EVALUATE_EXPRESSION,
    CMD_EXEC_EXPRESSION,
    CMD_EXIT,
    CMD_GET_ARRAY,
    CMD_GET_BREAKPOINT_EXCEPTION,
    CMD_GET_COMPLETIONS,
    #CMD_GET_CONCURRENCY_EVENT,
    CMD_GET_DESCRIPTION,
    CMD_GET_FILE_CONTENTS,
    #CMD_GET_FRAME,
    #CMD_GET_VARIABLE,
    CMD_IGNORE_THROWN_EXCEPTION_AT,
    #CMD_INPUT_REQUESTED,
    #CMD_LIST_THREADS,
    CMD_LOAD_SOURCE,
    CMD_PROCESS_CREATED,
    CMD_RELOAD_CODE,
    #CMD_REMOVE_BREAK,
    CMD_REMOVE_DJANGO_EXCEPTION_BREAK,
    #CMD_REMOVE_EXCEPTION_BREAK,
    #CMD_RETURN,
    #CMD_RUN,
    CMD_RUN_CUSTOM_OPERATION,
    CMD_RUN_TO_LINE,
    #CMD_SEND_CURR_EXCEPTION_TRACE,
    #CMD_SEND_CURR_EXCEPTION_TRACE_PROCEEDED,
    #CMD_SET_BREAK,
    CMD_SET_NEXT_STATEMENT,
    CMD_SET_PROPERTY_TRACE,
    CMD_SET_PY_EXCEPTION,
    CMD_SHOW_CONSOLE,
    CMD_SHOW_RETURN_VALUES,
    #CMD_SIGNATURE_CALL_TRACE,
    CMD_SMART_STEP_INTO,
    #CMD_STEP_CAUGHT_EXCEPTION,
    #CMD_STEP_INTO,
    CMD_STEP_INTO_MY_CODE,
    #CMD_STEP_OVER,
    #CMD_STEP_RETURN,
    #CMD_THREAD_CREATE,
    CMD_THREAD_KILL,
    #CMD_THREAD_RUN,
    #CMD_THREAD_SUSPEND,
    #CMD_VERSION,
    CMD_WRITE_TO_CONSOLE,
)


if sys.version_info[0] == 2:
    raise unittest.SkipTest('not tested under Python 2')


def _iter_usage(lines, regex, get_kind):
    cmds = []
    kind = None
    for line in lines:
        if cmds and kind:
            for cmd in cmds:
                yield cmd, kind
            cmds = []
            kind = None

        # Look for the kind.
        old = kind
        kind = get_kind(line) if get_kind else None
        if kind and old is not None:
            raise NotImplementedError

        # Look for the command.
        match = regex.match(line)
        if not match:
            continue
        if 'if reason == ' in line:
            continue
        cmd = match.group('cmd')
        if line.strip() == 'pydevd_comm.' + cmd + ',':
            continue
        cmd = getattr(_commands, cmd)
        cmds.append(cmd)
        yield cmd, None

    if cmds and kind:
        for cmd in cmds:
            yield cmd, kind
    else:
        assert(not (kind or cmds))


class SupportedTests(unittest.TestCase):

    REGEX = re.compile(r'.*pydevd_comm.(?P<cmd>CMD_[A-Z_]*)')

    def _get_kind(self, line):
        if '@pydevd_events.handler(' in line:
            return 'event'
        elif 'self.pydevd_request(' in line:
            return 'request'
        elif 'self.pydevd_notify(' in line:
            return 'notice'
        elif 'self.proc.pydevd_notify(' in line:
            return 'notice'
        else:
            return None

    # XXX TODO Get this test working.
    @unittest.skip('...for now.')
    def test_recorded(self):
        regex = self.REGEX
        get_kind = self._get_kind

        found = set()
        bykind = {
            'event': set(),
            'request': set(),
            'notice': set(),
        }
        srcdir = os.path.dirname(ptvsd.__file__)
        for filename in glob(os.path.join(srcdir, '*.py')):
            with open(filename) as pyfile:
                for cmd, kind in _iter_usage(pyfile, regex, get_kind):
                    found.add(cmd)
                    if kind is None:
                        continue
                    bykind[kind].add(cmd)

        self.assertEqual(found - _commands.IGNORED,
                         _commands.SUPPORTED_ALL)
        self.assertEqual(bykind['request'],
                         _commands.SUPPORTED_RESPONSES)
        self.assertEqual(bykind['request'] | bykind['notice'],
                         _commands.SUPPORTED_REQUESTS)
        self.assertEqual(bykind['event'],
                         _commands.SUPPORTED_EVENTS)

    def test_kinds(self):
        self.assertEqual(
            _commands.SUPPORTED_ALL,
            _commands.SUPPORTED_REQUESTS | _commands.SUPPORTED_EVENTS,
        )

        # Ensure all the responses are also listed as requests.
        self.assertFalse(_commands.SUPPORTED_RESPONSES -
                         _commands.SUPPORTED_REQUESTS -
                         _commands.POSSIBLE_RESPONSES_ONLY)

    def test_possible(self):
        self.assertFalse(
            _commands.SUPPORTED_ALL - _commands.POSSIBLE_ALL)
        self.assertFalse(
            _commands.SUPPORTED_REQUESTS - _commands.POSSIBLE_REQUESTS)
        self.assertFalse(_commands.SUPPORTED_RESPONSES -
                         set(_commands.POSSIBLE_RESPONSES))
        self.assertFalse(
            _commands.SUPPORTED_EVENTS - _commands.POSSIBLE_EVENTS)

    def test_unsupported(self):
        self.assertEqual(
            _commands.POSSIBLE_REQUESTS - _commands.SUPPORTED_REQUESTS,
            {
                CMD_ADD_DJANGO_EXCEPTION_BREAK,
                CMD_CONSOLE_EXEC,
                CMD_ENABLE_DONT_TRACE,
                CMD_EVALUATE_CONSOLE_EXPRESSION,
                CMD_EVALUATE_EXPRESSION,
                CMD_EXEC_EXPRESSION,
                CMD_GET_ARRAY,
                CMD_GET_COMPLETIONS,
                CMD_GET_DESCRIPTION,
                CMD_GET_FILE_CONTENTS,
                CMD_IGNORE_THROWN_EXCEPTION_AT,
                CMD_LOAD_SOURCE,
                CMD_RELOAD_CODE,
                CMD_REMOVE_DJANGO_EXCEPTION_BREAK,
                CMD_RUN_CUSTOM_OPERATION,
                CMD_RUN_TO_LINE,
                CMD_SET_NEXT_STATEMENT,
                CMD_SET_PROPERTY_TRACE,
                CMD_SET_PY_EXCEPTION,
                CMD_SHOW_RETURN_VALUES,
                CMD_SMART_STEP_INTO,
                CMD_STEP_INTO_MY_CODE,
                CMD_THREAD_KILL,
            },
        )
        self.assertEqual(
            _commands.POSSIBLE_RESPONSES - _commands.SUPPORTED_RESPONSES,
            {
                CMD_EVALUATE_CONSOLE_EXPRESSION,
                CMD_EVALUATE_EXPRESSION,
                CMD_GET_ARRAY,
                CMD_GET_COMPLETIONS,
                CMD_GET_DESCRIPTION,
                CMD_GET_FILE_CONTENTS,
                CMD_LOAD_SOURCE,
                CMD_RUN_CUSTOM_OPERATION,
            },
        )
        self.assertEqual(
            (set(_commands.POSSIBLE_RESPONSES_BY_REQUEST) -
             _commands.SUPPORTED_REQUESTS),
            {
                CMD_CONSOLE_EXEC,
                CMD_EVALUATE_CONSOLE_EXPRESSION,
                CMD_EVALUATE_EXPRESSION,
                CMD_EXEC_EXPRESSION,
                CMD_GET_ARRAY,
                CMD_GET_COMPLETIONS,
                CMD_GET_DESCRIPTION,
                CMD_GET_FILE_CONTENTS,
                CMD_LOAD_SOURCE,
                CMD_RUN_CUSTOM_OPERATION,
            },
        )
        self.assertEqual(
            _commands.POSSIBLE_EVENTS - _commands.SUPPORTED_EVENTS,
            {
                CMD_EXIT,
                CMD_GET_BREAKPOINT_EXCEPTION,
                CMD_PROCESS_CREATED,
                CMD_SHOW_CONSOLE,
                CMD_WRITE_TO_CONSOLE,
            },
        )


class PossibleTests(unittest.TestCase):

    CMD_RE = re.compile(r'.*(NetCommand[(](?:str[(])?)?(?P<cmd>CMD_[A-Z_]*)')
    MAKE_RE = re.compile(r'.*\.cmd_factory\.(make_[a-z_]*)[(]')
    INTERNAL_RE = re.compile(r'.*int_cmd = (Internal[A-Z_]*)[(]')

    BUNDLE = os.path.dirname(_pydevd.__file__)

    def _iter_event_calls(self):
        filename = os.path.join(os.path.dirname(self.BUNDLE), 'pydevd.py')
        with open(filename) as pyfile:
            for line in pyfile:
                match = self.MAKE_RE.match(line)
                if match:
                    method, = match.groups()
                    yield method, None
                else:
                    match = self.INTERNAL_RE.match(line)
                    if match:
                        internal, = match.groups()
                        yield None, internal

    def _iter_internal_commands(self):
        for name, obj in vars(_pydevd).items():
            if not name.startswith('Internal'):
                continue
            if not isinstance(obj, type):
                raise NotImplementedError
            if obj is _pydevd.InternalThreadCommand:
                continue
            if not issubclass(obj, _pydevd.InternalThreadCommand):
                raise NotImplementedError

            method = None
            error = False
            added = False
            for line in inspect.getsource(obj.do_it).splitlines():
                if '.make_error_message(' in line:
                    error = True
                elif 'dbg.writer.add_command(cmd)' in line:
                    added = True
                else:
                    match = self.MAKE_RE.match(line)
                    if match:
                        if method is not None:
                            raise NotImplementedError
                        method, = match.groups()
            if method:
                if not added:
                    raise NotImplementedError
                yield name, method, error

    def _iter_factory_methods(self):
        MAKE_DEF_RE = re.compile(
            r'^    def (make_[a-z_]*)\(.*(, dbg=None)?\):')
        #names = {name
        #         for name in dir(_pydevd.NetCommandFactory)
        #         if name.startswith('make_')}
        name = None
        cmd = None
        error = False
        async = False
        src = inspect.getsource(_pydevd.NetCommandFactory)
        for line in src.splitlines():
            if line.startswith('    def'):
                if name is not None:
                    print(name)
                    if cmd is None:
                        raise NotImplementedError
                    yield name, cmd, error, bool(async)
                    name = None
                    cmd = None
                    error = False
                    async = False

                match = MAKE_DEF_RE.match(line)
                if match:
                    name, async = match.groups()
            elif name is None:
                continue
            elif 'self.make_error_message(' in line:
                error = True
            else:
                match = self.CMD_RE.match(line)
                if match:
                    print(line)
                    nc, found = match.groups()
                    if nc:
                        if cmd:
                            raise NotImplementedError
                        cmd = found
        if name is not None:
            if cmd is None:
                raise NotImplementedError
            yield name, cmd, error, bool(async)

    def _iter_requests(self):
        REQ_RE = re.compile(
            r'^            (:?el)?if (cmd_id == CMD_[A-Z_]* .*):')
        filename = os.path.join(self.BUNDLE, 'pydevd_process_net_command.py')
        with open(filename) as pyfile:
            cmds = None
            method = None
            internal = None
            error = False
            for line in pyfile:
                if line.startswith('            else:'):
                    break

                match = REQ_RE.match(line)
                if match:
                    if cmds is not None:
                        for cmd in cmds:
                            yield cmd, method, internal, error
                        cmds = []
                        method = None
                        internal = None
                        error = False

                    comps, = match.groups()
                    for comp in comps.split(' or '):
                        _, _, cmd = comp.partition(' == ')
                        cmds.append(cmd)
                elif '.cmd_factory.make_error_message(' in line:
                    error = True
                else:
                    match = self.MAKE_RE.match(line)
                    if match:
                        if not cmd:
                            raise NotImplementedError
                        if method or internal:
                            raise NotImplementedError
                        method, = match.groups()
                    else:
                        match = self.INTERNAL_RE.match(line)
                        if match:
                            if not cmd:
                                raise NotImplementedError
                            if internal or method:
                                raise NotImplementedError
                            internal, = match.groups()
            if cmd is not None:
                yield cmd, method, internal, error

    def _parse_commands(self):
        names = set(name
                    for name in dir(_pydevd)
                    if name.startswith('CMD_'))

        factory = {}
        for method, cmd, _, _ in self._iter_factory_methods():
            self.assertIn(cmd, names)
            factory[method] = cmd

        internal = {}
        for name, method, _ in self._iter_internal_commands():
            self.assertIn(method, factory)
            internal[name] = method

        events = set()
        for method, name in self._iter_event_calls():
            self.assertIn(method, factory)
            if method is None:
                method = internal[name]
            cmd = factory[method]
            events.add(cmd)

        requests = {}
        for cmd, method, name, _ in self._iter_requests():
            self.assertIn(cmd, names)
            if method is not None:
                response = factory[method]
            elif name is not None:
                method = internal[name]
                response = factory[method]
            else:
                response = None
            requests[cmd] = response

        return names, requests, events

    # XXX TODO Get this test working.
    @unittest.skip('...for now.')
    def test_recorded(self):
        found, requests, events = self._parse_commands()

        self.assertEqual(_commands.PYDEVD_ALL, found)

        # requests (from adapter)
        self.assertEqual(_commands.POSSIBLE_REQUESTS, set(requests))
        self.assertEqual(_commands.POSSIBLE_RESPONSES,
                         {req: resp
                          for req, resp in requests.items()
                          if resp is not None})
        self.assertEqual(_commands.POSSIBLE_EVENTS, events)

    def test_all(self):
        self.assertEqual(_commands.POSSIBLE_ALL | _commands.IGNORED,
                         _commands.PYDEVD_ALL)

    def test_kinds(self):
        _commands.POSSIBLE_ALL
        self.assertEqual(
            _commands.POSSIBLE_ALL,
            (_commands.POSSIBLE_REQUESTS |
             _commands.POSSIBLE_RESPONSES |
             _commands.POSSIBLE_PYDEVD_REQUESTS |
             _commands.POSSIBLE_EVENTS),
        )

        # Ensure all the responses are also listed as requests.
        self.assertFalse(_commands.POSSIBLE_PYDEVD_RESPONSES -
                         _commands.POSSIBLE_PYDEVD_REQUESTS)
        self.assertFalse(_commands.POSSIBLE_RESPONSES -
                         _commands.POSSIBLE_REQUESTS -
                         _commands.POSSIBLE_RESPONSES_ONLY)
        self.assertEqual(_commands.POSSIBLE_RESPONSES_ONLY -
                         _commands.POSSIBLE_REQUESTS,
                         _commands.POSSIBLE_RESPONSES_ONLY)
