import sys
print("before")
sys.stdout.write("no newline")
sys.stdout.write("\n")
sys.stderr.write("to stderr\n")
sys.exit(3)
print("after")
