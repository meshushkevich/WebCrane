# =========
# Colorama
# =========
from colorama import init
init(autoreset=True)

# ====================
# Parse client arguments
# ====================
from argparse import ArgumentParser

parser = ArgumentParser(
    prog = 'wsvcs',
    description = 'WebSockets Version Control System',
)
parser.add_argument('mode', help='''
init   - Initialize current directory as project
deploy - Use this device as middleware server
pull   - Create pull request
push   - Create push request
client    - Open Command Line Interface
''')
args = parser.parse_args()


# ======================
# Standard functional
# ======================
valid_commands = ['init', 'deploy', 'pull', 'push', 'client', 'run']

# ======================
# Constants
# ======================
LENGTH_OF_PATH_IN_PBAR = 64
HASHING_THREADS        = 3
GROUPING_THREADS       = 3
#                   mb    bytes
PACKAGE_MAX_SIZE = 512 * 1024


#  256 * 1024   - 10.35
#  384 * 1024   -  8.22
#  512 * 1024   -  8.02
#  768 * 1024   -  9.22
# 1024 * 1024 - too big
