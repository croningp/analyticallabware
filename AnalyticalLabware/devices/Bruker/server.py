from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler

import otofcontrol as oc

# Create server
server = SimpleXMLRPCServer(("0.0.0.0", 8000),
                            allow_none=True,
                            use_builtin_types=True)

server.register_introspection_functions()

with oc.BrukerMS(rpc=True) as handle:
    server.register_instance(handle)
    server.serve_forever()