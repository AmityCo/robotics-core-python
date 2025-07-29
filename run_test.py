#!/usr/bin/env python3
"""
Simple script to run the answer API test
Make sure your server is running before executing this script
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the test
if __name__ == "__main__":
    # Import here to avoid path issues
    from test.test_answer import main
    main()
