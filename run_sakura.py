import runpy
import sys
import os

# Add the parent directory of sakura_assistant to sys.path
# This makes 'sakura_assistant' discoverable as a package
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now, execute main.py as a module within the sakura_assistant package
from sakura_assistant.main import main  # or whatever your main entry point is

main() 