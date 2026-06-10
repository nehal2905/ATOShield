import os
import sys

# Make `import features` work regardless of pytest's invocation cwd.
sys.path.insert(0, os.path.dirname(__file__))
