#!/usr/bin/env python3
"""Fake Hermes CLI."""
import sys

if "-q" in sys.argv:
    i = sys.argv.index("-q")
    if i + 1 < len(sys.argv):
        print("HERMES_Q:", sys.argv[i + 1][:120])
sys.exit(0)
