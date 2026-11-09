from mine_core import run_mining

ROUNDS = 1

# The shared runner checks unlocks and clears before mining.
run_mining("rice", ROUNDS, 0, -1)
