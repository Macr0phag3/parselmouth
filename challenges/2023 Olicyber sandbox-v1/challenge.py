#!/usr/bin/env python3
import sys
import code

# for code.InteractiveConsole to send stack traces to stdout
sys.excepthook = sys.__excepthook__

class RestrictedConsole(code.InteractiveConsole):
	def __init__(self, locals, blacklist, *a, **kw):
		super().__init__(locals, *a, **kw)
		self.blacklist = blacklist.copy()
		
	def runsource(self, source, *a, **kw):
		if not source.isascii() or any(word in source for word in self.blacklist):
			print("Blacklisted word detected, exiting ...")
			sys.exit(1)
		return super().runsource(source, *a, **kw)
	
	def write(self, data):
		sys.stdout.write(data)

# keep all the builtins except open
safe_builtins = {
	k:v for k,v in __builtins__.__dict__.items() if k != "open" 
}
locals = {'__builtins__': safe_builtins}

blacklist = ['import', 'os', 'system', 'subproces', 'sh', 'flag']

RestrictedConsole(locals, blacklist).interact()
