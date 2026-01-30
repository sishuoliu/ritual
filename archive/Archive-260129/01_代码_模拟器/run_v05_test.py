# -*- coding: utf-8 -*-
"""
Simplified test runner with file output to bypass PowerShell issues
"""

import sys
import os

# Redirect stdout to file
output_file = open('test_results_v05.txt', 'w', encoding='utf-8')
sys.stdout = output_file

# Import and run the simulator
import coop_game_simulator_v05_balanced

# Run the tests
coop_game_simulator_v05_balanced.run_test_suite()

# Close file
output_file.close()

print("Test complete. Results written to test_results_v05.txt")
