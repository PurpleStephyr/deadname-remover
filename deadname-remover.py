#!/bin/env python3
# Copyright 2024 Steph Kraemer

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import subprocess
import re

class Main():
    def __init__(self):
        parser = argparse.ArgumentParser(prog='deadname-remover', description='Tool to remove deadnames from git history')
        parser.add_argument('-n', '--names', required=True)
        parser.add_argument('-d', '--deadnames', required=True)
        parser.add_argument('-c', '--case-sensitive', help='Always use the same case as name (deadnames are matched with any case)',
                            action='store_true')

        self.args = parser.parse_args()

        self.names = self.args.names.split(',')
        self.deadnames = self.args.deadnames.split(',')
        self.deadname_re = '(' + '|'.join(re.escape(deadname) for deadname in self.deadnames) + ')'
        self.author = subprocess.check_output(['git', 'config', 'user.name']).decode()
        self.email = subprocess.check_output(['git', 'config', 'user.email']).decode()

    def run(self):

        if len(self.names) == 1:
            self.names *= len(self.deadnames)

        if len(self.names) != len(self.deadnames):
            print("You must provide the same number of names to replace deadnames with, or exactly one name to replace multiple deadnames with")
            return 1

        branch = subprocess.check_output(['git', 'branch', '--show-current']).decode().strip()
        new_branch = f'deadname-remover/{branch if branch != "master" else "main"}'
        commit_shas = subprocess.check_output(['git', 'log', '--format=format:%H']).decode().splitlines()
        commit_shas.reverse()

        for i, commit_sha in enumerate(commit_shas):
            show_output = subprocess.check_output(['git', 'show', commit_sha]).decode()
            if any(deadname.lower() in show_output.lower() for deadname in self.deadnames):
                break
        if i == 0:
            subprocess.check_output(['git', 'checkout', '-b', new_branch, commit_sha])
            self.remove_deadname_from_last_commit(show_output)
        else:
            subprocess.check_output(['git', 'checkout', '-b', new_branch, commit_shas[i-1]])

        for i in range(i+1, len(commit_shas)):
            try:
                subprocess.check_output(['git', 'cherry-pick', commit_shas[i]])
            except subprocess.CalledProcessError as e:
                _ = input("cherry-pick failed - resolve, run 'git cherry-pick --continue', and press <Enter> to continue")
            show_output = subprocess.check_output(['git', 'show', commit_shas[i]]).decode()
            if any(deadname.lower() in show_output.lower() for deadname in self.deadnames):
                self.remove_deadname_from_last_commit(show_output)

    def remove_deadname_from_last_commit(self, show_output):
        for j, deadname in enumerate(self.deadnames):
            try:
                for file in subprocess.check_output(['git', 'grep', '--name-only', '-i', deadname]).decode().splitlines():
                    if not self.args.case_sensitive:
                        # replaces lowercase with lowercase, uppercase with uppercase, any other case with name case
                        subprocess.check_output(['sed', '-i', f's/{deadname}/{self.names[j]}/g', file])
                        subprocess.check_output(['sed', '-i', f's/{deadname.lower()}/{self.names[j].lower()}/g', file])
                        subprocess.check_output(['sed', '-i', f's/{deadname.upper()}/{self.names[j].upper()}/g', file])
                    subprocess.check_output(['sed', '-i', f's/{deadname}/{self.names[j]}/Ig', file]) # sed 'I' option matches any case
            except subprocess.CalledProcessError as _:
                # git grep returns failure if pattern not found
                pass
        m = re.search(r'^Author:.*' + self.deadname_re, show_output, flags=re.MULTILINE)
        if m:
            author_opts = [f'--author={self.author} <{self.email}>']
        else:
            author_opts = []
        message = subprocess.check_output(['git', 'log', '-1', "--format=format:%B"]).decode()
        for j, deadname in enumerate(self.deadnames):
            message = message.replace(deadname, self.names[j]) 
        subprocess.check_output(['git', 'commit', '-a', '--amend', '-m', message] + author_opts)



if __name__ == '__main__':
    main = Main()
    exit(main.run())