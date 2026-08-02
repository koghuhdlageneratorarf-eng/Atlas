from core.patch_engine import PatchEngine

pe = PatchEngine()
diff = '''--- test_error.py
+++ test_error.py
@@ -6,7 +6,7 @@
 def main():
     def print_goodbye():
         say_hello()
         print("Goodbye")
-    print("Hello")
-        print_goodbye()
+    print("Hello")
+    print_goodbye()
'''

result = pe.apply_patch('test_error.py', diff, dry_run=False)
print(result)