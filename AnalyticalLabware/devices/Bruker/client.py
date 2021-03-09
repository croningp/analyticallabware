from xmlrpc.client import ServerProxy

class OtofControl:
    def __init__(self, ip: str, port: int):
        self.proxy = ServerProxy(f"http://{ip}:{port}")
        for method in self.proxy.system.listMethods():
            setattr(self, method, getattr(self.proxy, method))
            f = getattr(self, method)
            f.__doc__ = self.proxy.system.methodHelp(method)