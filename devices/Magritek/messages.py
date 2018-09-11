from textwrap import dedent

ABORT = '''
<?xml version="1.0" encoding="UTF-8"?>
<Message>
<Abort/>
</Start>
</Message>
'''.strip()

CALL_NMR = '''
<?xml version="1.0" encoding="UTF-8"?>
<Message>
<Start protocol="1D PROTON">
<Option name="Scan" value="QuickScan" />
</Start>
</Message>
'''.strip()

CHECK_SHIM = '''
<?xml version="1.0" encoding="UTF-8"?>
<Message>
<Start protocol="SHIM">
<Option name="Shim" value="CheckShim" />
</Start>
</Message>
'''.strip()

QUICK_SHIM = '''
<?xml version="1.0" encoding="UTF-8"?>
<Message>
<Start protocol="SHIM">
<Option name="Shim" value="QuickShim" />
</Start>
</Message>
'''.strip()

