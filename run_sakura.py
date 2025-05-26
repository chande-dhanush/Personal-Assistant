import runpy
import sys
import os

# Add the parent directory of sakura_assistant to sys.path
# This makes 'sakura_assistant' discoverable as a package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now, execute main.py as a module within the sakura_assistant package
# This mimics 'python -m sakura_assistant.main'
runpy.run_module('sakura_assistant.main', run_name="__main__", alter_sys=True)