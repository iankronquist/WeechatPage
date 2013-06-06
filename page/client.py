import sys

from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.python import log

from page import config
from page.notify import notify
from page.parser import parse_message, bytes_to_int
from page.utils import clean_formatting


class RelayProtocol(Protocol):

    def __init__(self, *args, **kwargs):
        self._buffer = ''
        self.weechat_buffers = {}
        reactor.addSystemEventTrigger('before', 'shutdown', self.end)

    # Twisted methods.

    def connectionMade(self):
        self.transport.write('init password={password},compression=off\n'
                             .format(**config))
        self.transport.write('(buffer_list) hdata buffer:gui_buffers(*) '
                             'name\n')
        self.transport.write('sync\n')

    def dataReceived(self, data):
        self._buffer += data

        # If there are less than 4 bytes, we can't parse expected length
        # yet, so just chill.
        while len(self._buffer) >= 4:
            # if there are enough bytes, pop a message from the buffer.
            expected_len = bytes_to_int(self._buffer[:4])
            if len(self._buffer) >= expected_len:
                self._pop_message()
            else:
                break

    # Helper methods

    def _pop_message(self):
        expected_len = bytes_to_int(self._buffer[:4])

        # Pop the message from the buffer
        to_parse = self._buffer[:expected_len]
        self._buffer = self._buffer[expected_len:]

        # Parse it
        msg_id, message = parse_message(to_parse)

        # process it
        if msg_id.startswith('_'):
            msg_id = 'sys' + msg_id

        if msg_id is None:
            msg_id = 'misc'

        msg_id = 'msg_' + msg_id

        try:
            getattr(self, msg_id)(message)
        except AttributeError as e:
            log.err('Unknown message id: "%s"' % msg_id)
            log.err(e)

    def end(self):
        self.transport.write('quit\n')
        self.transport.loseConnection()

    def _should_notify(self, line):
        displayed = line['displayed'] == '\x01'
        highlight = line['highlight'] == '\x01'
        message = 'irc_privmsg' in line['tags_array']
        private = 'notify_private' in line['tags_array']

        return displayed and message and (highlight or private)

    # Weechat messages

    def msg_buffer_list(self, msg):
        self.weechat_buffers.update({
            b['_pointers'][0][1]: b['name']
            for b in msg[0]['values']
        })

    def msg_sys_buffer_line_added(self, msg):
        """When a message is received, notify if appropriate."""

        # All lines, if they match the notify critera.

        for line in (l for l in msg[0]['values'] if self._should_notify(l)):
            buf_name = self.weechat_buffers[line['buffer']]
            notify(clean_formatting('{buf_name} - {prefix} - {message}'
                                    .format(buf_name=buf_name, **line)))

    def msg_sys_buffer_opened(self, msg):
        """When a buffer is added, sync it."""

        val = msg[0]['values'][0]

        _, pointer = val['_pointers'][0]
        self.transport.write('sync %s *\n' % pointer)

        if 'name' in val:
            name = val['name']
        else:
            name = val['local_variables']['name']

        self.weechat_buffers[pointer] = name

    def msg_sys_buffer_closing(self, msg):
        """When a buffer is removed, desync it."""

        _, pointer = msg[0]['values'][0]['_pointers'][0]
        self.transport.write('desync %s *\n' % pointer)
        del self.weechat_buffers[pointer]

    # Unused Weechat messages

    def msg_sys_nicklist(self, msg):
        pass

    def msg_sys_nicklist_diff(self, msg):
        pass

    def msg_sys_buffer_localvar_added(self, msg):
        pass

    def msg_sys_buffer_localvar_removed(self, msg):
        pass

    def msg_sys_buffer_localvar_changed(self, msg):
        pass

    def msg_sys_buffer_title_changed(self, msg):
        pass

    def msg_sys_buffer_renamed(self, msg):
        pass


class RelayFactory(ClientFactory):

    def buildProtocol(self, addr):
        return RelayProtocol()


def main():
    log.startLogging(sys.stdout)
    reactor.connectTCP(config['host'], config['port'], RelayFactory())
    reactor.run()


if __name__ == '__main__':
    main()
