from textwrap import dedent
from typing import List, Union

HEADER = '<?xml version="1.0" encoding="UTF-8"?>'

class Node:
    def __init__(self, *children, **attrs):
        self.tag = getattr(self.__class__, 'tag', self.__class__.__name__ + 'Type')
        self.attrs = attrs
        self.children = children
    def __str__(self):
        tag = self.__class__.__name__
        attrs = ' '.join(f"k='{self.attrs[k]}'" for k in self.attrs)
        children = '\n'.join(str(c) for c in self.children)
        attrs = attrs and ' ' + attrs
        if children:
            return f'<{tag}{attrs}>\n{children}\n</{self.tag}>'
        return f'<{tag}{attrs}>/>'

class StringNode(Node):
    def __init__(self, arg: str):
        super().__init__(arg)

class Option(Node):
    tag = 'Option'
    def __init__(self, name: str, value):
        super().__init__(name=name, value=value)

class Processing(Node):
    pass

# TODO: Flesh out args
class Start(Node):
    def __init__(self, protocol: str, *args: List[Node]):
        super().__init__(*args, protocol=protocol)

class Script(Node):
    def __init__(self, arg: str):
        super().__init__(arg)

class Execute(Node):
    def __init__(self, script: Script):
        super().__init__(script)

class Abort(Node):
    pass

class CheckShim(Node):
    tag = 'CheckShimRequestType'
    pass

class QuickShim(Node):
    tag = 'QuickShimRequestType'
    pass

class PowerShim(Node):
    tag = 'PowerShimRequestType'
    pass

class HardwareRequest(Node):
    pass

class EstimateDuration(Node):
    tag = 'EstimateDurationRequestType'
    def __init__(self, protocol: str, *options: List[Option]):
        super().__init__(*options, protocol=protocol)

class ProtocolOptions(Node):
    tag = 'ProtocolOptionsRequestType'
    def __init__(self, protocol: str):
        super().__init__(protocol=protocol)

class AvailableProtocolOptions(Node):
    tag = 'AvailableProtocolOptionsRequestType'

class AvailableOptions(Node):
    tag = 'AvailableOptionsRequestType'
    def __init__(self, protocol: str):
        super().__init__(protocol=protocol)

class AvailableProtocols(Node):
    tag = 'AvailableProtocolsRequestType'

class Selection(Node):
    def __init__(self, protocol: str, options: List[Option]):
        super().__init__(*options, protocol=protocol)

class Solvent(StringNode):
    tag = 'Solvent'

class Sample(StringNode):
    tag = 'Sample'

class TimeStamp(StringNode):
    tag = 'TimeStamp'

class TimeStampTree(StringNode):
    tag = 'TimeStampTree'

class UserFolder(StringNode):
    tag = 'UserFolder'

class Data(Node):
    tag = 'Data'
    def __init__(self, key: str, value: str):
        super().__init__(key=key, value=value)

class UserData(Node):
    tag = 'UserData'
    def __init__(self, data: List[Data]):
        super().__init__(data)

class DataFolder(StringNode):
    tag = 'DataFolder'

class Set(Node):
    def __init__(self, arg: Union[Solvent, Sample, DataFolder, UserData]):
        super().__init__(arg)

class Message():
    def __init__(self, node: Node, header=HEADER):
        self.node = node
        self.header = header
    def __str__(self):
        return f'{self.header}\n{self.node}'

if __name__ == '__main__':
    print(Message(Set(Solvent('DMSO'))))

# CALL_NMR = '''
# <?xml version="1.0" encoding="UTF-8"?>
# <Message>
# <Start protocol="1D PROTON">
# <Option name="Scan" value="QuickScan" />
# </Start>
# </Message>
# '''.strip()

# CHECK_SHIM = '''
# <?xml version="1.0" encoding="UTF-8"?>
# <Message>
# <Start protocol="SHIM">
# <Option name="Shim" value="CheckShim" />
# </Start>
# </Message>
# '''.strip()

# QUICK_SHIM = '''
# <?xml version="1.0" encoding="UTF-8"?>
# <Message>
# <Start protocol="SHIM">
# <Option name="Shim" value="QuickShim" />
# </Start>
# </Message>
# '''.strip()

