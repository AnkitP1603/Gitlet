


import os

from src.ignore import gitignore_check, gitignore_read
from src.objects.objects import object_find, object_hash
from src.objects.tree import tree_to_dict
from src.refs import ref_resolve
from src.utils import get_active_branch


def cmd_status_branch(repo):
    branch = get_active_branch(repo)
    if branch:
        print(f"On branch {branch}")
    else:
        print(f"HEAD detached at {object_find(repo, 'HEAD')}")
        
        
def cmd_status_head_index(repo,index):
    print("Changes to be committed:")
    
    head_sha = ref_resolve(repo, "HEAD")

    if head_sha:
        head = tree_to_dict(repo, "HEAD")
    else:
        head = {}
    
    for entry in index.entries:
        if entry.name in head:
            if head[entry.name]!=entry.sha:
                print(f"\tmodified: {entry.name}")
            del head[entry.name]
        else:
            print(f"\tadded: {entry.name}")
            
    for entry in head.keys():
        print(f"\tdeleted: {entry}")
        
def cmd_status_index_worktree(repo,index):
    print("Changes not staged for commit:")
    
    ignore = gitignore_read(repo)
    
    gitdir_prefix = repo.gitdir + os.sep
    all_files = set()
    
    for (root,_,files) in os.walk(repo.worktree,True):
        if root==repo.gitdir or root.startswith(gitdir_prefix):
            continue
        
        for f in files:
            full_path = os.path.join(root,f)
            rel_path = os.path.relpath(full_path, repo.worktree)
            all_files.add(rel_path)
            
    for entry in index.entries:
        full_path = os.path.join(repo.worktree, entry.name)
        
        if not os.path.exists(full_path):
            print(f"\tdeleted: {entry.name}")
        else:
            stat = os.stat(full_path)
            
            ctime_ns = entry.ctime[0]*10**9 + entry.ctime[1]
            mtime_ns = entry.mtime[0]*10**9 + entry.mtime[1]
            
            if stat.st_ctime_ns != ctime_ns or stat.st_mtime_ns != mtime_ns:
                # If different, deep compare.
                # @FIXME This *will* crash on symlinks to dir.
                with open(full_path, "rb") as fd:
                    new_sha = object_hash(fd, b"blob", None)
                    # If the hashes are the same, the files are actually the same.
                    same = entry.sha == new_sha
                    if not same:
                        print(f"\tmodified: {entry.name}")
                        
        if entry.name in all_files:
            all_files.remove(entry.name)
            
    print()
    print("Untracked files:")
    for f in all_files:
        # @TODO If a full directory is untracked, we should display
        # its name without its contents.
        if not gitignore_check(ignore, f):
            print(f"\t{f}")