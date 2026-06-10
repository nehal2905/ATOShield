import os
import sys

# Make `import app...` work regardless of pytest invocation cwd.
sys.path.insert(0, os.path.dirname(__file__))
