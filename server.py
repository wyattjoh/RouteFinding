"""
Usage:  server.py stdin [options]
        server.py shell [options]
        server.py sock [options]
        server.py serial <port> [options]
        server.py [options]

Starts the python mapping server.

NOTE: For Assignment 3 Part 1, please execute
>> server.py

All requests will be made by simply providing and latitude and longitude (in 100,000ths of degrees) of
the start and end points in ASCII, separated by spaces and terminated by a newline.

Modes:
    stdin: The server will serve requests over stdin (Use for Assignment 3 Part 1)
        example
        contents of batch.txt: 5365488 -11333914 5364727 -11335890
        mapfile: edmonton-roads-2.0.1.txt
        >> server.py stdin < batch.txt
        8
        5365488 -11333914
        5365238 -11334423
        5365157 -11334634
        5365035 -11335026
        5364789 -11335776
        5364774 -11335815
        5364756 -11335849
        5364727 -11335890


Arguments:

Options:
  --graph <GRAPHFILE>  The file to load graph info [default: edmonton-roads-2.0.1.txt]
  --logfile <LOGFILE>  The location of the logfile [default: MappingServer.log]
  -h --help
  -v                 verbose mode

"""

import signal
import sys
import math
import docopt
import logging
import logging.handlers

from digraph import least_cost_path
from readgraph import readgraph
from async import run_async


class MappingServer:
    """
    Performs routing from any two points within the graphfile's boundries.

    """

    def __init__(self, arguments):
        """
        Arguments:
            arguments   a dictionary containing initialization information for the class
        """
        # create logger with 'spam_application'
        self.logger = logging.getLogger('MappingServer')
        self.logger.setLevel(logging.DEBUG)
        # create file handler which logs even debug messages
        fh = logging.handlers.RotatingFileHandler(arguments['--logfile'], maxBytes=10000)
        fh.setLevel(logging.DEBUG)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # add the handlers to the logger
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

        # enable a verbose logger to stream everything to the screen
        if arguments['-v']:
            vb = logging.StreamHandler()
            vb.setLevel(logging.DEBUG)
            vb.setFormatter(formatter)
            self.logger.addHandler(vb)
            self.logger.info("Verbose mode activated")

        # Read in graphfile into a graph object (self.G) and vertex names/data into (self.names)
        self.logger.info("Reading graphfile...")
        (self.G, self.names) = readgraph(arguments['--graph'])
        self.logger.info("Reading of graphfile finished. Graph available.")

        # Parse configuration options
        if arguments['stdin']:
            self._int_mode()
        elif arguments['shell']:
            import code
            code.interact(local=locals())
        elif arguments['sock']:
            self._sock_mode()
        elif arguments['serial'] and arguments['<port>']:
            self._serial_mode(arguments['<port>'])
        else:
            pass

    def _serial_mode(self, port):
        import serial

        self.logger.info("Opening serial port: {}".format(port))
        self.serial_out = self.serial_in = serial.Serial(port, 9600)

        try:
            idx = 0
            while True:
                msg = self._serial_receive()

                self.logger.debug("GOT:" + msg + ":")

                try:
                    point_1, point_2 = self._prepare_string(msg)
                except ValueError:
                    # self.logger.error("Invalid input> {}".format(msg.rstrip()))
                    continue

                # Compute the least_cost_path from the two points
                _lcp = self._lcp(point_1, point_2)

                self.logger.info("Sending LCP over serial...")

                if _lcp:
                    self._serial_send(len(_lcp))

                    for vertex_id in _lcp:

                        point = self.names[0][vertex_id]

                        point = self._coord_trans(point)

                        self._serial_send('{0[0]} {0[1]}'.format(point))

                self.logger.info("Serial send finished!")

                # Print the result using formatter function
                # self._print_lcp(_lcp)
                idx += 1

        except KeyboardInterrupt:
            pass

    def _serial_send(self, message):
        """
        Sends a message back to the client device.
        """
        full_message = ''.join((str(message), "\n"))

        # self.logger.debug("server:" + str(message) + ":")

        reencoded = bytes(full_message, encoding='ascii')
        self.serial_out.write(reencoded)

    def _serial_receive(self, timeout=None):
        """
        Listen for a message. Attempt to timeout after a certain number of
        milliseconds.
        """
        raw_message = self.serial_in.readline()

        # self.logger.debug("client:" + str(raw_message) + ":")

        message = raw_message.decode('ascii')

        return message.rstrip("\n\r")

    def _print_lcp(self, path):
        """
        Prints the _lcp in the desired format, displays nothing if there is no path.
        """
        if path:
            print(len(path))

            for vertex_id in path:

                point = self.names[0][vertex_id]

                point = self._coord_trans(point)

                print('{0[0]} {0[1]}'.format(point))

    def _json_lcp(self, path):
        """
        Returns a json string of the path, for use with the socket mode.
        """
        import json

        if path:

            points = []

            for vertex_id in path:

                point = self.names[0][vertex_id]

                points.append(point)

            return json.dumps(points)

    @run_async
    def _socket_request(self, connection, address):
        """
        Handles a socket request, parsing the input coords and outputting a json formmatted response
        """
        import ast

        self.logger.info(str(address[0]) + " Connection made, recieving data")

        buf = connection.recv(8400)

        if len(buf) > 0:
            coords = ast.literal_eval(buf.decode('utf-8'))

            base_coord = (self._coord_trans(coords[0]), self._coord_trans(coords[1]))

            try:
                if len(base_coord) != 2 or len(base_coord[0]) != 2 or len(base_coord[1]) != 2:
                    raise IndexError()
            except IndexError:
                connection.close()
                return

            self.logger.info(str(address[0]) + " Recieved data, sending reply.")
            self.logger.info(str(address[0]) + " Request to serve route from ({0[0]}, {0[1]}) to ({1[0]}, {1[1]})".format(base_coord[0], base_coord[1]))

            _lcp = self._lcp(base_coord[0], base_coord[1])

            if _lcp:
                self.logger.info(str(address[0]) + " Route will require {} steps".format(len(_lcp)))

                json_to_send = self._json_lcp(_lcp)

                connection.send(json_to_send.encode('utf-8'))
                self.logger.info(str(address[0]) + " Data sent")
            else:
                self.logger.info(str(address[0]) + " No route available")

            connection.close()
            self.logger.info(str(address[0]) + " Closed connection")
            return

    def _sock_sig_handler(self, signal, frame):
        """
        Handles a SIGINT signal, closing the socket connection, for use with socket mode.
        """
        self.logger.error("SIGINT caught during socket mode, closing socket..")
        try:
            self.serversocket.shutdown(self.serversocket.SHUT_RDWR)
        except OSError:
            pass
        self.serversocket.close()
        self.logger.error("Socket closed.")
        sys.exit(0)

    def _sock_mode(self):
        """
        Serves a mapping service over socket to a web service
        """
        import socket

        old_sig = signal.signal(signal.SIGINT, self._sock_sig_handler)

        try:
            self.logger.info("Binding to socket.")
            self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serversocket.bind(('localhost', 8089))
            self.serversocket.listen(10)

            while True:
                self.logger.info("Waiting for connection")

                while True:
                    connection, address = self.serversocket.accept()

                    self._socket_request(connection, address)

        except KeyboardInterrupt:
            try:
                self.serversocket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.serversocket.close()

        signal.signal(signal.SIGINT, old_sig)

    def _prepare_string(self, string):
        """
        Parses a input from stdin to a set of points
        """
        string = string.rstrip()
        (x1, y1, x2, y2) = string.split(" ")

        point_1 = (int(x1), int(y1))
        point_2 = (int(x2), int(y2))

        return (point_1, point_2)

    def _int_mode(self):
        """
        Standard input mode. Parses and returns directions from desired entry coordinates within the mapfiles boundries
        """
        self.logger.info("stdin startup mode selected")
        self.logger.info("Entering interactive request mode")
        self.request = sys.stdin

        try:
            for line in self.request:
                try:
                    point_1, point_2 = self._prepare_string(line)
                except ValueError:
                    self.logger.error("Invalid input> {}".format(line.rstrip()))
                    continue

                # Compute the least_cost_path from the two points
                _lcp = self._lcp(point_1, point_2)

                # Print the result using formatter function
                self._print_lcp(_lcp)

        except KeyboardInterrupt:
            pass

    def _coord_trans(self, coord):
        """
        Transforms decimal coordinates into 100,000ths of degrees
        """
        return (int(coord[0] * 100000), int(coord[1] * 100000))

    def _lookup_id(self, coord):
        """
        Looks up the closest id given a set of coordinates
        """
        coord_id = min(self.names[2].items(), key=lambda x: self._cost_function((coord, x[0]), True))[1]
        return coord_id

    def _cost_function(self, points, coords_ovr=False):
        """
        Computes the distance from a set of coordinates using a metric
        """
        try:
            if not coords_ovr:
                p1 = self.names[0][points[0]]
                p2 = self.names[0][points[1]]
            else:
                p1 = points[0]
                p2 = points[1]
        except KeyError:
            return None

        return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

    def _lcp(self, start_coord, dest_coord):
        """
        Computes the least_cost_path from start_coord to dest_coord
        """

        start = self._lookup_id(start_coord)
        dest = self._lookup_id(dest_coord)

        self.logger.info("Getting least_cost_path from ({}) to ({})".format(start_coord, dest_coord))

        return least_cost_path(self.G, start, dest, self._cost_function)

if __name__ == '__main__':
    # Started directly, parse command line options...
    arguments = docopt.docopt(__doc__)

    blank_check = ['stdin', 'shell', 'sock', 'serial']

    if not (arguments['stdin'] or arguments['shell'] or arguments['sock'] or arguments['serial']):
        arguments['stdin'] = True

    MappingServer(arguments)

else:
    # Started as module, prepare ms object for use with exported functions...
    arguments = {'--graph': 'edmonton-roads-2.0.1.txt', '--help': False, '--logfile': 'MappingServer.log', '-v': False, '<port>': None, 'serial': False, 'shell': False, 'sock': False, 'stdin': True}
    ms = MappingServer(arguments)

    def cost_distance(e):
        return ms._cost_function(e)
