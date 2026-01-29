# -*- coding: utf-8 -*-
"""Launcher: run balance tuning from repo root (avoids cd to path with non-ASCII)."""
import sys
import os
base = os.path.dirname(os.path.abspath(__file__))
sim_dir = os.path.join(base, "桌游", "模拟测试")
if not os.path.isdir(sim_dir):
    print("Sim dir not found:", sim_dir)
    sys.exit(1)
sys.path.insert(0, sim_dir)
os.chdir(sim_dir)
import balance_tuning_v36
balance_tuning_v36.main()
