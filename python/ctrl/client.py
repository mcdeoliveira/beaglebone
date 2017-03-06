import warnings
import socket

from . import packet
import ctrl

class WrapSocket:

    def __init__(self, socket):
        self.socket = socket

    def read(self, bufsize = 1):
        buffer = b''
        while bufsize:
            temp = self.socket.recv(bufsize)
            bufsize -= len(temp)
            buffer += temp
        return buffer

class Controller(ctrl.Controller):

    def __init__(self, *vargs, **kwargs):

        # parameters
        self.host = kwargs.pop('host', 'localhost')
        self.port = kwargs.pop('port', 9999)

        self.socket = None
        self.shutdown_request = False

        # Initialize controller
        super().__init__(*vargs, **kwargs)

        self.debug = 1

    def __enter__(self):
        if self.debug > 0:
            print('> Opening socket')
        self.open()
        super().__enter__()
        return self

    def __exit__(self, type, value, traceback):
        super().__exit__(type, value, traceback)
        if self.debug > 0:
            print('> Closing socket')
        self.close()

    def open(self):
        # Open a socket
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
        else:
            warnings.warn("Socket already open")

    def close(self):
        if self.socket is None:
            warnings.warn("Socket is not open")
        else:
            self.socket.close()
            self.socket = None
            
    def send(self, command, *vargs):

        # Make sure vargs is in pairs
        n = len(vargs)
        assert n % 2 == 0

        # Open socket if closed
        auto_close = False
        if self.socket is None:
            self.open()
            auto_close = True

        # Send command to server
        if self.debug > 0:
            print("> Will request command '{}'"
                  .format(command))
        self.socket.send(packet.pack('C', command))

        # Send arguments to server
        for (argtype, argvalue) in (vargs[i:i+2] for i in range(0, n, 2)):
            if self.debug > 0:
                print("> Will send argument '{}({})'"
                      .format(argtype, argvalue))
            self.socket.send(packet.pack(argtype, argvalue))

        # Wait for output
        if self.debug > 0:
            print("> Waiting for stream...")
        (type, value) = packet.unpack_stream(WrapSocket(self.socket))

        if type == 'A':

            if self.debug > 0:
                print("> Received Acknowledgment '{}'\n".format(value))
            value = None

        else: # if type != 'A':

            if self.debug > 0:
                print("> Received type = '{}', value = '{}'"
                      .format(type, value))

            if self.debug > 0:
                print("> Waiting for acknowledgment...")
            (type_, value_) = packet.unpack_stream(WrapSocket(self.socket))

            if type_ == 'A':

                if self.debug > 0:
                    print("> Received Acknowledgment '{}'\n".format(value))

            else: # if type != 'A':

                warnings.warn('Failed to receive acknowledgment')

        # Close socket
        if auto_close:
            self.close()

        # If error, raise exception
        if type == 'E':
            raise value

        return value

    # Controller methods
    def help(self, value = ''):
        return self.send('A', 'S', value)

    def info(self, options = 'summary'):
        return self.send('B', 'S', options)

    def reset(self):
        return self.send('Z')

    # signals
    def add_signal(self, label):
        self.send('C', 'S', label)

    def set_signal(self, label, values):
        self.send('D', 'S', label, 'P', values)

    def get_signal(self, label):
        return self.send('E', 'S', label)

    def get_signals(self, *labels):
        return self.send('e', 'R', labels)

    def list_signals(self):
        return self.send('F')

    def remove_signal(self, label):
        self.send('G', 'S', label)

    # sources
    def add_source(self, label, source, signals, order = -1):
        self.send('H', 'S', label, 'P', source, 'P', signals, 'I', order)

    def set_source(self, label, **kwargs):
        self.send('I', 'S', label, 'K', kwargs)

    def get_source(self, label, *keys):
        return self.send('i', 'S', label, 'R', keys)

    def remove_source(self, label):
        return self.send('J', 'S', label)

    def list_sources(self):
        return self.send('K')

    def write_source(self, label, *values):
        self.send('L', 'S', label, 'R', values)

    def read_source(self, label):
        return self.send('M', 'S', label)


    # sinks
    def add_sink(self, label, sink, signals, order = -1):
        self.send('N', 'S', label, 'P', sink, 'P', signals, 'I', order)

    def set_sink(self, label, **kwargs):
        self.send('O', 'S', label, 'K', kwargs)

    def get_sink(self, label, *keys):
        return self.send('o', 'S', label, 'R', keys)

    def remove_sink(self, label):
        return self.send('P', 'S', label)

    def list_sinks(self):
        return self.send('Q')

    def write_sink(self, label, *values):
        self.send('R', 'S', label, 'R', values)

    def read_sink(self, label):
        return self.send('S', 'S', label)


    # filters

    def add_filter(self, label, filter_, 
                   input_signals, output_signals,
                   order = -1):
        self.send('T', 'S', label, 'P', filter_, 
                  'P', input_signals, 'P', output_signals, 
                  'I', order)

    def set_filter(self, label, **kwargs):
        self.send('U', 'S', label, 'K', kwargs)

    def get_filter(self, label, *keys):
        return self.send('u', 'S', label, 'R', keys)

    def remove_filter(self, label):
        return self.send('V', 'S', label)

    def list_filters(self):
        return self.send('W')

    def write_filter(self, label, *values):
        self.send('X', 'S', label, 'R', values)

    def read_filter(self, label):
        return self.send('Y', 'S', label)

    # devices
    def add_device(self, label, device_module, device_class, **kwargs):
        self.send('z', 'S', label, 'S', device_module, 'S', device_class, 'K', kwargs)

    # def set_period(self, value):
    #     return self.send('a', 'D', value)

    # def get_period(self):
    #     return self.send('b')

    def start(self):
        self.send('c')

    def stop(self):
        if not self.shutdown_request:
            self.send('d')

    def shutdown(self):
        self.shutdown_request = True
        self.send('0')

