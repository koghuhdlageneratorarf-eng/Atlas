from core.self_debug import SelfDebugger

error = """Traceback (most recent call last):
  File "test_error.py", line 9, in <module>
    main()
  File "test_error.py", line 6, in main
    print_goodbye()
NameError: name 'print_goodbye' is not defined
"""

debugger = SelfDebugger()
debugger.max_attempts = 1  # чтобы быстрее

# Временно переопределим generate_fix, чтобы видеть diff
original_generate = debugger.generate_fix

def debug_generate(error_info, previous_attempts=None):
    diff = original_generate(error_info, previous_attempts)
    print("\n=== GENERATED DIFF ===")
    print(diff)
    print("=== END DIFF ===\n")
    return diff

debugger.generate_fix = debug_generate

result = debugger.debug_cycle(error)
print("RESULT:", result)

# Проверим, изменился ли файл
with open("test_error.py", "r") as f:
    print("\n=== CURRENT test_error.py ===\n", f.read())