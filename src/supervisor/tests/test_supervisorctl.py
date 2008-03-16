import sys
import unittest
from StringIO import StringIO

from supervisor.tests.base import DummyRPCServer

class ControllerTests(unittest.TestCase):
    def _getTargetClass(self):
        from supervisor.supervisorctl import Controller
        return Controller

    def _makeOne(self, options):
        return self._getTargetClass()(options)

    def test_ctor(self):
        options = DummyClientOptions()
        controller = self._makeOne(options)
        self.assertEqual(controller.prompt, options.prompt + '> ')

    def test__upcheck(self):
        options = DummyClientOptions()
        controller = self._makeOne(options)
        result = controller.upcheck()
        self.assertEqual(result, True)

    def test__upcheck_wrong_server_version(self):
        options = DummyClientOptions()
        options._server.supervisor.getVersion = lambda *x: '1.0'
        controller = self._makeOne(options)
        controller.stdout = StringIO()
        result = controller.upcheck()
        self.assertEqual(result, False)
        value = controller.stdout.getvalue()
        self.assertEqual(value, 'Sorry, this version of supervisorctl expects '
        'to talk to a server with API version 3.0, but the remote version is '
        '1.0.\n')

    def test__upcheck_unknown_method(self):
        options = DummyClientOptions()
        from xmlrpclib import Fault
        from supervisor.xmlrpc import Faults
        def getVersion():
            raise Fault(Faults.UNKNOWN_METHOD, 'duh')
        options._server.supervisor.getVersion = getVersion
        controller = self._makeOne(options)
        controller.stdout = StringIO()
        result = controller.upcheck()
        self.assertEqual(result, False)
        value = controller.stdout.getvalue()
        self.assertEqual(value, 'Sorry, supervisord responded but did not '
        'recognize the supervisor namespace commands that supervisorctl '
        'uses to control it.  Please check that the '
        '[rpcinterface:supervisor] section is enabled in the '
        'configuration file (see sample.conf).\n')

    def test_onecmd(self):
        options = DummyClientOptions()
        controller = self._makeOne(options)
        controller.stdout = StringIO()
        plugin = DummyPlugin()
        controller.options.plugins = (plugin,)
        result = controller.onecmd('help')
        self.assertEqual(result, None)
        self.assertEqual(plugin.helped, True)

    def test_onecmd_multi_colonseparated(self):
        options = DummyClientOptions()
        controller = self._makeOne(options)
        controller.stdout = StringIO()
        plugin = DummyPlugin()
        controller.options.plugins = (plugin,)
        result = controller.onecmd('help; help')
        self.assertEqual(result, None)
        self.assertEqual(controller.cmdqueue, [' help'])
        self.assertEqual(plugin.helped, True)
        
class TestDefaultPlugin(unittest.TestCase):

    def _getTargetClass(self):
        from supervisor.supervisorctl import DefaultControllerPlugin
        return DefaultControllerPlugin

    def _makeOne(self, *arg, **kw):
        klass = self._getTargetClass()
        options = DummyClientOptions()
        ctl = DummyController(options)
        plugin = klass(ctl, *arg, **kw)
        return plugin

    def test_tail_toofewargs(self):
        plugin = self._makeOne()
        result = plugin.do_tail('')
        self.assertEqual(result, None)
        lines = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(lines[0], 'Error: too few arguments')

    def test_tail_toomanyargs(self):
        plugin = self._makeOne()
        result = plugin.do_tail('one two three four')
        self.assertEqual(result, None)
        lines = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(lines[0], 'Error: too many arguments')

    def test_tail_f_noprocname(self):
        plugin = self._makeOne()
        result = plugin.do_tail('-f')
        self.assertEqual(result, None)
        lines = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(lines[0], 'Error: tail requires process name')

    def test_tail_defaults(self):
        plugin = self._makeOne()
        result = plugin.do_tail('foo')
        self.assertEqual(result, None)
        lines = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(len(lines), 12)
        self.assertEqual(lines[0], 'output line')

    def test_tail_no_file(self):
        plugin = self._makeOne()
        result = plugin.do_tail('NO_FILE')
        lines = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], 'NO_FILE: ERROR (no log file)')

    def test_tail_failed(self):
        plugin = self._makeOne()
        result = plugin.do_tail('FAILED')
        lines = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], 'FAILED: ERROR (unknown error reading log)')

    def test_tail_bad_name(self):
        plugin = self._makeOne()
        result = plugin.do_tail('BAD_NAME')
        lines = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], 'BAD_NAME: ERROR (no such process name)')

    def test_tail_bytesmodifier(self):
        plugin = self._makeOne()
        result = plugin.do_tail('-10 foo')
        self.assertEqual(result, None)
        lines = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], 'tput line')

    def test_tail_explicit_channel_stdout_nomodifier(self):
        plugin = self._makeOne()
        result = plugin.do_tail('foo stdout')
        self.assertEqual(result, None)
        lines = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(len(lines), 12)
        self.assertEqual(lines[0], 'output line')

    def test_tail_explicit_channel_stderr_nomodifier(self):
        plugin = self._makeOne()
        result = plugin.do_tail('foo stderr')
        lines = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(len(lines), 12)
        self.assertEqual(lines[0], 'output line')

    def test_tail_explicit_channel_unrecognized(self):
        plugin = self._makeOne()
        result = plugin.do_tail('foo fudge')
        self.assertEqual(result, None)
        value = plugin.ctl.stdout.getvalue().strip()
        self.assertEqual(value, "Error: bad channel 'fudge'")

    def test_status_oneprocess(self):
        plugin = self._makeOne()
        result = plugin.do_status('foo')
        self.assertEqual(result, None)
        value = plugin.ctl.stdout.getvalue().strip()
        self.assertEqual(value.split(None, 2),
                         ['foo', 'RUNNING', 'foo description'])
                         

    def test_status_allprocesses(self):
        plugin = self._makeOne()
        result = plugin.do_status('')
        self.assertEqual(result, None)
        value = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(value[0].split(None, 2),
                         ['foo', 'RUNNING', 'foo description'])
        self.assertEqual(value[1].split(None, 2),
                         ['bar', 'FATAL', 'bar description'])
        self.assertEqual(value[2].split(None, 2),
                         ['baz:baz_01', 'STOPPED', 'baz description'])

    def test_start_fail(self):
        plugin = self._makeOne()
        result = plugin.do_start('')
        self.assertEqual(result, None)
        expected = "Error: start requires a process name"
        self.assertEqual(plugin.ctl.stdout.getvalue().split('\n')[0], expected)

    def test_start_badname(self):
        plugin = self._makeOne()
        result = plugin.do_start('BAD_NAME')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'BAD_NAME: ERROR (no such process)\n')

    def test_start_alreadystarted(self):
        plugin = self._makeOne()
        result = plugin.do_start('ALREADY_STARTED')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'ALREADY_STARTED: ERROR (already started)\n')

    def test_start_spawnerror(self):
        plugin = self._makeOne()
        result = plugin.do_start('SPAWN_ERROR')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'SPAWN_ERROR: ERROR (spawn error)\n')

    def test_start_one_success(self):
        plugin = self._makeOne()
        result = plugin.do_start('foo')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(), 'foo: started\n')

    def test_start_many(self):
        plugin = self._makeOne()
        result = plugin.do_start('foo bar')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'foo: started\nbar: started\n')

    def test_start_group(self):
        plugin = self._makeOne()
        result = plugin.do_start('foo:')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'foo_00: started\nfoo_01: started\n')

    def test_start_all(self):
        plugin = self._makeOne()
        result = plugin.do_start('all')
        self.assertEqual(result, None)

        self.assertEqual(plugin.ctl.stdout.getvalue(),
                'foo: started\nfoo2: started\nfailed: ERROR (spawn error)\n')


    def test_stop_fail(self):
        plugin = self._makeOne()
        result = plugin.do_stop('')
        self.assertEqual(result, None)
        expected = "Error: stop requires a process name"
        self.assertEqual(plugin.ctl.stdout.getvalue().split('\n')[0], expected)

    def test_stop_badname(self):
        plugin = self._makeOne()
        result = plugin.do_stop('BAD_NAME')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'BAD_NAME: ERROR (no such process)\n')

    def test_stop_notrunning(self):
        plugin = self._makeOne()
        result = plugin.do_stop('NOT_RUNNING')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'NOT_RUNNING: ERROR (not running)\n')

    def test_stop_failed(self):
        plugin = self._makeOne()
        result = plugin.do_stop('FAILED')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(), 'FAILED\n')

    def test_stop_one_success(self):
        plugin = self._makeOne()
        result = plugin.do_stop('foo')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(), 'foo: stopped\n')

    def test_stop_many(self):
        plugin = self._makeOne()
        result = plugin.do_stop('foo bar')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'foo: stopped\nbar: stopped\n')

    def test_stop_group(self):
        plugin = self._makeOne()
        result = plugin.do_stop('foo:')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'foo_00: stopped\nfoo_01: stopped\n')

    def test_stop_all(self):
        plugin = self._makeOne()
        result = plugin.do_stop('all')
        self.assertEqual(result, None)

        self.assertEqual(plugin.ctl.stdout.getvalue(),
         'foo: stopped\nfoo2: stopped\nfailed: ERROR (no such process)\n')

    def test_restart_fail(self):
        plugin = self._makeOne()
        result = plugin.do_restart('')
        self.assertEqual(result, None)

        self.assertEqual(plugin.ctl.stdout.getvalue().split('\n')[0],
         'Error: restart requires a process name')

    def test_restart_one(self):
        plugin = self._makeOne()
        result = plugin.do_restart('foo')
        self.assertEqual(result, None)

        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'foo: stopped\nfoo: started\n')

    def test_restart_all(self):
        plugin = self._makeOne()
        result = plugin.do_restart('all')
        self.assertEqual(result, None)

        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         ('foo: stopped\nfoo2: stopped\n'
                          'failed: ERROR (no such process)\n'
                          'foo: started\nfoo2: started\n'
                          'failed: ERROR (spawn error)\n'))

    def test_clear_fail(self):
        plugin = self._makeOne()
        result = plugin.do_clear('')
        self.assertEqual(result, None)
        expected = "Error: clear requires a process name"
        self.assertEqual(plugin.ctl.stdout.getvalue().split('\n')[0], expected)

    def test_clear_badname(self):
        plugin = self._makeOne()
        result = plugin.do_clear('BAD_NAME')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'BAD_NAME: ERROR (no such process)\n')

    def test_clear_one_success(self):
        plugin = self._makeOne()
        result = plugin.do_clear('foo')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(), 'foo: cleared\n')

    def test_clear_many(self):
        plugin = self._makeOne()
        result = plugin.do_clear('foo bar')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'foo: cleared\nbar: cleared\n')

    def test_clear_all(self):
        plugin = self._makeOne()
        result = plugin.do_clear('all')
        self.assertEqual(result, None)

        self.assertEqual(plugin.ctl.stdout.getvalue(),
         'foo: cleared\nfoo2: cleared\nfailed: ERROR (failed)\n')

    def test_open_fail(self):
        plugin = self._makeOne()
        result = plugin.do_open('badname')
        self.assertEqual(result, None)
        self.assertEqual(plugin.ctl.stdout.getvalue(),
                         'ERROR: url must be http:// or unix://\n')

    def test_open_succeed(self):
        plugin = self._makeOne()
        result = plugin.do_open('http://localhost:9002')
        self.assertEqual(result, None)
        value = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(value[0].split(None, 2),
                         ['foo', 'RUNNING', 'foo description'])
        self.assertEqual(value[1].split(None, 2),
                         ['bar', 'FATAL', 'bar description'])
        self.assertEqual(value[2].split(None, 2),
                         ['baz:baz_01', 'STOPPED', 'baz description'])

    def test_version(self):
        plugin = self._makeOne()
        plugin.do_version(None)
        self.assertEqual(plugin.ctl.stdout.getvalue(), '3000\n')

    def test_reload_fail(self):
        plugin = self._makeOne()
        options = plugin.ctl.options
        options._server.supervisor._restartable = False
        result = plugin.do_reload('')
        self.assertEqual(result, None)
        self.assertEqual(options._server.supervisor._restarted, False)
        
    def test_reload(self):
        plugin = self._makeOne()
        options = plugin.ctl.options
        result = plugin.do_reload('')
        self.assertEqual(result, None)
        self.assertEqual(options._server.supervisor._restarted, True)
        
    def test_shutdown_fail(self):
        plugin = self._makeOne()
        options = plugin.ctl.options
        options._server.supervisor._restartable = False
        result = plugin.do_shutdown('')
        self.assertEqual(result, None)
        self.assertEqual(options._server.supervisor._shutdown, False)

    def test_shutdown(self):
        plugin = self._makeOne()
        options = plugin.ctl.options
        result = plugin.do_shutdown('')
        self.assertEqual(result, None)
        self.assertEqual(options._server.supervisor._shutdown, True)

    def test_pid(self):
        plugin = self._makeOne()
        result = plugin.do_pid('')
        options = plugin.ctl.options
        self.assertEqual(result, None)
        lines = plugin.ctl.stdout.getvalue().split('\n')
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], str(options._server.supervisor.getPID()))

class DummyClientOptions:
    def __init__(self):
        self.prompt = 'supervisor'
        self.serverurl = 'http://localhost:9001'
        self.username = 'chrism'
        self.password = '123'
        self.history_file = None
        self.plugins = ()
        self._server = DummyRPCServer()
        self.interactive = False
        self.plugin_factories = []

    def getServerProxy(self):
        return self._server

class DummyController:
    def __init__(self, options):
        self.options = options
        self.stdout = StringIO()
        
    def upcheck(self):
        return True

    def get_supervisor(self):
        return self.options.getServerProxy().supervisor

    def output(self, data):
        self.stdout.write(data + '\n')

class DummyPlugin:
    def __init__(self, controller=None):
        self.ctl = controller
        
    def do_help(self, arg):
        self.helped = True

def test_suite():
    return unittest.findTestCases(sys.modules[__name__])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

