from git import *
import os
from os import path as p
import shutil
import json

CONFIG = p.join(p.dirname(p.abspath(__file__)), 'config.json')

with open(CONFIG, 'r') as f:
    config = json.load(f)

DATA_LOC = config['data location']
os.makedirs(p.join(DATA_LOC, config['project']))
shutil.copy(CONFIG, p.join(DATA_LOC, config['project'], 'config.json'))
