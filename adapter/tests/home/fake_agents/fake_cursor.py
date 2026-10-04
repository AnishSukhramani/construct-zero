#!/usr/bin/env python3
"""Fake Cursor agent CLI for integration tests."""

import sys

for i, arg in enumerate(sys.argv):
    if arg == "-p" and i + 1 < len(sys.argv):
        print("HANDOFF_PROMPT:", sys.argv[i + 1][:200])
        break
print('{"result":"ok"}')
sys.exit(0)
