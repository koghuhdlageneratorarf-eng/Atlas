from core.self_debug import SelfDebugger

d = SelfDebugger()
error = 'Traceback (most recent call last):\n  File "atlas_core/agent.py", line 958, in main\n    print_welcome()\nNameError: name "print_welcome" is not defined'
info = d.analyze_traceback(error)
diff = d.generate_fix(info)
print('DIFF:', diff)