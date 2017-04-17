import sys
from time import sleep

from PyQt4 import QtCore
import rtmidi

#from const import *
from midiutils import *
INPUT, OUTPUT = xrange(2)

class RtMidiSequencer(QtCore.QObject):
    ''' A fake sequencer object that emulates ALSA sequencer'''
    conn_created = QtCore.pyqtSignal(object)
    conn_destroyed = QtCore.pyqtSignal(object)
    client_created = QtCore.pyqtSignal(object)
    client_destroyed = QtCore.pyqtSignal(object)
    port_created = QtCore.pyqtSignal(object)
    port_destroyed = QtCore.pyqtSignal(object)
    midi_event = QtCore.pyqtSignal(object, object)

    def __init__(self, clientname):
        QtCore.QObject.__init__(self)
        self.clientname = clientname
        self.api = rtmidi.get_compiled_api()[0]
        self.listener_in = rtmidi.MidiIn(self.api, clientname)
        self.listener_in.ignore_types(sysex=False)
        self.listener_out = rtmidi.MidiOut(self.api, clientname)
        self.ports = {INPUT: [self.listener_in], OUTPUT: [self.listener_out]}
        self.connections = {self.listener_in: None, self.listener_out: None}
        self.default_in_caps = 66
        self.default_out_caps = 33
        self.default_type = 1048578
        self.alsa_mode = True if 'linux' in sys.platform else False
        self.in_graph_dict = {}
        self.out_graph_dict = {}
        self.client_dict = {}

    def update_graph(self):
        previous_out_clients = self.out_graph_dict.keys()
        previous_in_clients = self.in_graph_dict.keys()
        if self.alsa_mode:
            for previous_list in previous_out_clients, previous_in_clients:
                for port_name in previous_list:
                    if port_name.startswith('Bigglesworth:'):
                        previous_list.pop(previous_list.index(port_name))
        new_out_clients = []
        for port_name in self.listener_in.get_ports():
            if self.alsa_mode and port_name.startswith('Bigglesworth:'):
                continue
            if port_name in previous_out_clients:
                previous_out_clients.pop(previous_out_clients.index(port_name))
            else:
                new_out_clients.append(port_name)
        if previous_out_clients:
            for port_name in previous_out_clients:
                self.out_graph_dict.pop(port_name)
                client_id = self.client_dict.keys()[self.client_dict.values().index(port_name)]
                self.client_dict.pop(client_id)
                print 'emit port "{}" removed'.format(port_name)
                self.port_destroyed.emit({'addr.client': client_id, 'addr.port': 0})
                self.client_destroyed.emit({'addr.client': client_id})
        new_index = 0
        if new_out_clients:
            new_index = max(self.client_dict.keys()) + 1
            for port_name in new_out_clients:
                self.client_dict[new_index] = port_name
                self.out_graph_dict[port_name] = new_index
                print 'emit port "{}" added'.format(port_name)
                self.client_created.emit({'addr.client': new_index})
                self.port_created.emit({'addr.client': new_index, 'addr.port': 0})
                new_index += 1

        new_in_clients = []
        for port_name in self.listener_out.get_ports():
            if self.alsa_mode and port_name.startswith('Bigglesworth:'):
                continue
            if port_name in previous_in_clients:
                previous_in_clients.pop(previous_in_clients.index(port_name))
            else:
                new_in_clients.append(port_name)
        if previous_in_clients:
            for port_name in previous_in_clients:
                self.in_graph_dict.pop(port_name)
                self.client_dict.pop(self.client_dict.values().index(port_name))
                print 'emit port "{}" removed'.format(port_name)
                self.port_destroyed.emit({'addr.client': client_id, 'addr.port': 0})
                self.client_destroyed.emit({'addr.client': client_id})
        if new_in_clients:
            for port_name in new_in_clients:
                self.client_dict[new_index] = port_name
                self.in_graph_dict[port_name] = new_index
                print 'emit port "{}" added'.format(port_name)
                self.client_created.emit({'addr.client': new_index})
                self.port_created.emit({'addr.client': new_index, 'addr.port': 0})
                new_index += 1

    def connection_list(self):
        delta_id = 0
        res_list = []
        if self.alsa_mode:
            res_list.append(('Bigglesworth', 0, [('input', 0, ([], []))]))
            self.client_dict[0] = self.clientname + ':input'
            self.in_graph_dict['Bigglesworth:input'] = 0
            res_list.append(('Bigglesworth', 0, [('output', 1, ([], []))]))
            self.client_dict[1] = self.clientname + ':output'
            self.out_graph_dict['Bigglesworth:output'] = 1
            delta_id = 2
        for in_id, port_name in enumerate(self.listener_in.get_ports(), delta_id):
            self.out_graph_dict[port_name] = in_id
            self.client_dict[in_id] = port_name
        for out_id, port_name in enumerate(self.listener_out.get_ports(), in_id + 1):
            self.in_graph_dict[port_name] = out_id
            self.client_dict[out_id] = port_name
        for client_id, name in self.client_dict.items():
            res_list.append((name, client_id, [(name, 0, ([], []))]))
        return res_list

    def get_client_info(self, client_id):
        if not client_id in self.client_dict:
            raise BaseException
        return {
                'name': self.client_dict[client_id], 
                'id': client_id, 
                'broadcast_filter': 0, 
                'error_bounce': 0, 
                'event_filter': '', 
                'event_lost': 0, 
                'num_ports': 1, 
                'type': 2
                }

    def get_port_info(self, port_id, client_id):
        if client_id in self.in_graph_dict.values():
            caps = self.default_in_caps
        else:
            caps = self.default_out_caps
        return {
                'capability': caps, 
                'name': self.client_dict[client_id], 
                'type': self.default_type, 
                }

    def connect_ports(self, source, dest, *args):
        source = source[0]
        dest = dest[0]
        if source == 1:
            for port in self.ports[OUTPUT]:
                if self.connections[port]: continue
                break
            else:
                port = rtmidi.MidiOut(self.api, 'Bigglesworth')
                self.ports[OUTPUT].append(port)
            dest_name = self.client_dict[dest]
            port.open_port(port.get_ports().index(dest_name), 'output')
            self.connections[port] = dest_name
            self.conn_created.emit({'connect.sender.client': 1, 'connect.sender.port': 0, 'connect.dest.client': dest, 'connect.dest.port': 0})

        else:
            for port in self.ports[INPUT]:
                if self.connections[port]: continue
                break
            else:
                port = rtmidi.MidiIn(self.api, 'Bigglesworth')
                port.ignore_types(sysex=False)
                self.ports[INPUT].append(port)
            source_name = self.client_dict[source]
            port.open_port(port.get_ports().index(source_name), 'input')
            port.set_callback(self.midi_event.emit)
            self.connections[port] = source_name
            self.conn_created.emit({'connect.sender.client': source, 'connect.sender.port': 0, 'connect.dest.client': 0, 'connect.dest.port': 0})

    def disconnect_ports(self, source, dest):
        source = source[0]
        dest = dest[0]
        if source == 1:
            target_name = self.client_dict[dest]
        else:
            target_name = self.client_dict[source]
        for port, dest in self.connections.items():
            if target_name == dest:
                port.close_port()
                self.connections[port] = None
                break
        else:
#            raise rtmidi.RtMidiError('Error disconnecting ports')
#            print 'connection already removed?'
            return
        if source == 1:
            self.conn_destroyed.emit({'connect.sender.client': 1, 'connect.sender.port': 0, 'connect.dest.client': dest, 'connect.dest.port': 0})
        else:
            self.conn_destroyed.emit({'connect.sender.client': source, 'connect.sender.port': 0, 'connect.dest.client': 0, 'connect.dest.port': 0})

    def get_connect_info(self, source, dest):
        source = source[0]
        dest = dest[0]
        if source == 1:
            target_name = self.client_dict[dest]
        else:
            target_name = self.client_dict[source]
        for port, dest in self.connections.items():
            if target_name == dest:
#                port.close_port()
#                self.connections[port] = None
                break
        else:
#            print 'connection does not exist'
            raise
        return {'exclusive': 0, 'queue': 0, 'time_real': 0, 'time_update': 0}


class MidiDevice(QtCore.QObject):
#    client_start = QtCore.pyqtSignal(object)
#    client_exit = QtCore.pyqtSignal(object)
#    port_start = QtCore.pyqtSignal(object)
#    port_exit = QtCore.pyqtSignal(object)
#    conn_register = QtCore.pyqtSignal(object, bool)
#    graph_changed = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    midi_event = QtCore.pyqtSignal(object)

    def __init__(self, main):
        QtCore.QObject.__init__(self)
        self.main = main
        self.type = RTMIDI
        self.active = False
        self.sysex_buffer = []
#        self.seq = alsaseq.Sequencer(clientname='Bigglesworth')
        self.seq = RtMidiSequencer(clientname='Bigglesworth')
        self.keep_going = True
#        input_id = self.seq.create_simple_port(
#            name='input', 
#            type=alsaseq.SEQ_PORT_TYPE_MIDI_GENERIC|alsaseq.SEQ_PORT_TYPE_APPLICATION, 
#            caps=alsaseq.SEQ_PORT_CAP_WRITE|alsaseq.SEQ_PORT_CAP_SUBS_WRITE|
#            alsaseq.SEQ_PORT_CAP_SYNC_WRITE)
#        output_id = self.seq.create_simple_port(name='output', 
#                                                type=alsaseq.SEQ_PORT_TYPE_MIDI_GENERIC|alsaseq.SEQ_PORT_TYPE_APPLICATION, 
#                                                caps=alsaseq.SEQ_PORT_CAP_READ|alsaseq.SEQ_PORT_CAP_SUBS_READ|
#                                                alsaseq.SEQ_PORT_CAP_SYNC_READ)

#        self.seq.connect_ports((alsaseq.SEQ_CLIENT_SYSTEM, alsaseq.SEQ_PORT_SYSTEM_ANNOUNCE), (self.seq.client_id, input_id))
#        self.api = rtmidi.get_compiled_api()[0]
#        input_port = rtmidi.MidiIn(self.api, 'Bigglesworth')
#        output_port = rtmidi.MidiOut(self.api, 'Bigglesworth')
#        self.ports = {INPUT: [input_port], OUTPUT: [output_port]}
#        self.connections = {input_port: None, output_port: None}
        self.graph = self.main.graph = AlsaGraph(self.seq)
        self.seq.client_created.connect(self.graph.client_created)
        self.seq.client_destroyed.connect(self.graph.client_destroyed)
        self.seq.port_created.connect(self.graph.port_created)
        self.seq.port_destroyed.connect(self.graph.port_destroyed)
        self.seq.conn_created.connect(self.graph.conn_created)
        self.seq.conn_destroyed.connect(self.graph.conn_destroyed)
        self.seq.midi_event.connect(self.create_midi_event)
#        self.graph.conn_register.connect(self.conn_register)
#        self.id = self.seq.client_id
#        self.input = self.graph.port_id_dict[self.id][input_id]
#        self.output = self.graph.port_id_dict[self.id][output_id]
        self.input = self.graph.port_id_dict[0][0]
        self.output = self.graph.port_id_dict[1][0]

    def create_midi_event(self, (data, time), *args):
        newev = MidiEvent.from_binary(data)
        self.midi_event.emit(newev)

    def run(self):
        self.active = True
        while self.keep_going:
            try:
                #better use qtimer in seq
                sleep(.1)
                self.seq.update_graph()
#                event_list = self.seq.receive_events(timeout=1024, maxevents=1)
#                for event in event_list:
#                    data = event.get_data()
#                    if event.type == alsaseq.SEQ_EVENT_CLIENT_START:
#                        self.graph.client_created(data)
#                    elif event.type == alsaseq.SEQ_EVENT_CLIENT_EXIT:
#                        self.graph.client_destroyed(data)
#                    elif event.type == alsaseq.SEQ_EVENT_PORT_START:
#                        self.graph.port_created(data)
#                    elif event.type == alsaseq.SEQ_EVENT_PORT_EXIT:
#                        self.graph.port_destroyed(data)
#                    elif event.type == alsaseq.SEQ_EVENT_PORT_SUBSCRIBED:
#                        self.graph.conn_created(data)
#                    elif event.type == alsaseq.SEQ_EVENT_PORT_UNSUBSCRIBED:
#                        self.graph.conn_destroyed(data)
#                    elif event.type in [alsaseq.SEQ_EVENT_NOTEON, alsaseq.SEQ_EVENT_NOTEOFF, 
#                                        alsaseq.SEQ_EVENT_CONTROLLER, alsaseq.SEQ_EVENT_PGMCHANGE,
#                                        ]:
#                        try:
#                            newev = MidiEvent.from_alsa(event)
#                            self.midi_event.emit(newev)
##                            print newev
#                        except Exception as e:
#                            print 'event {} unrecognized'.format(event)
#                            print e
#                    elif event.type in [alsaseq.SEQ_EVENT_CLOCK, alsaseq.SEQ_EVENT_SENSING]:
#                        pass
#                    elif event.type == alsaseq.SEQ_EVENT_SYSEX:
#                        self.check(event)
            except Exception as e:
                print e
                print 'something is wrong'
#        print 'stopped'
        print 'exit'
        del self.seq
        self.stopped.emit()

    def check(self, event):
        data = event.get_data()['ext']
        try:
            if data[0] == 0xf0:
                self.buffer = data
            else:
                self.buffer.extend(data)
#            print 'sysex message length: {}'.format(len(self.buffer))
            if data[-1] != 0xf7:
                return
            else:
                sysex = MidiEvent.from_alsa(event)
                sysex.sysex = self.buffer
                self.midi_event.emit(sysex)
                self.buffer = []
        except Exception as Err:
            print len(self.buffer)
            print Err
