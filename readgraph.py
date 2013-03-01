"""
    python3 readgraph.py [ digraph-file ]

Takes a csv (comma separated values) text file containing the vertices
and edges of a street digraph and converts it into a digraph instance.

If the optional argument digraph-file is supplied, reads that, otherwise
takes input from stdin
"""
# import sys

# # throw away executable name before processing command line arguments
# argv = sys.argv[1:]

# # if filename is supplied, use that, otherwise use stdin
# if argv:
#     digraph_file_name = argv.pop(0)
#     digraph_file = open(digraph_file_name, 'r')
# else:
#     digraph_file = sys.stdin

# For testing, just use a simple representation of set of vertices, set of
# edges as ordered pairs, and dctionaries that map
#   vertex to (lat,long)
#   edge to street name

import logging
from digraph import Digraph


def readgraph(digraph_file_name):
    # create logger
    readgraph_logger = logging.getLogger('MappingServer.readgraph')

    readgraph_logger.info("Opening graphfile:" + str(digraph_file_name))
    digraph_file = open(digraph_file_name, 'r')
    readgraph_logger.info("Open successful.")

    V = set()
    E = set()
    V_coord = {}
    E_name = {}

    G = Digraph()

    readgraph_logger.info("Parsing file...")
    # process each line in the file
    for line in digraph_file:

        # strip all trailing whitespace
        line = line.rstrip()

        fields = line.split(",")
        type = fields[0]

        if type == 'V':
            # got a vertex record
            (id, lat, long) = fields[1:]

            # vertex id's should be ints
            id = int(id)

            # lat and long are floats
            lat = float(lat)
            long = float(long)

            V.add(id)
            V_coord[id] = (lat, long)

        elif type == 'E':
            # got an edge record
            (start, stop, name) = fields[1:]

            # vertices are ints
            start = int(start)
            stop = int(stop)
            e = (start, stop)

            # get rid of leading and trailing quote " chars around name
            name = name.strip('"')

            # consistency check, we don't want auto adding of vertices when
            # adding an edge.
            if start not in V or stop not in V:
                readgraph_logger.error("Edge {} has an endpoint that is not a vertex".format(e))
                raise Exception("Edge {} has an endpoint that is not a vertex".format(e))

            G.add_edge(e)
            E_name[e] = name
        else:
            # weird input
            readgraph_logger.error("Error: weird line |{}|".format(line))
            raise Exception("Error: weird line |{}|".format(line))

    readgraph_logger.info("Parsing finished.")
    readgraph_logger.debug("Graph has " + str(G.num_vertices()) + " vertices and " + str(G.num_edges()) + " edges")

    V_Rev = {}

    for key in V_coord:
        V_Rev[key] = (int(V_coord[key][0] * 100000), int(V_coord[key][1] * 100000))

    V_coord_rev = dict([(v, k) for (k, v) in V_Rev.items()])

    names = (V_coord, E_name, V_coord_rev)

    return (G, names)
