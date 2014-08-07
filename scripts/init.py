from git import *
import os

DATA_LOC = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ), '..', '..', 'data')

repo = Repo.init(
    DATA_LOC,
    bare=False
)

repo.create_remote('master', 'git@github.com:nivekmai/config.git')
