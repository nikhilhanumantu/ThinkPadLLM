import sys
import os

# Add the backend directory to sys.path so modules like app are fully resolvable
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from run import app
