from core.self_debug import SelfDebugger
debugger = SelfDebugger()
error = """Traceback (most recent call last):
  File "atlas_core/agent.py", line 958, in main
    print_welcome()
NameError: name 'print_welcome' is not defined"""
result = debugger.debug_cycle(error)
print(result)