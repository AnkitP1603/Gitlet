from src.repository import repo_file, repo_find
import os
from src.objects.index import index_read
from src.objects.objects import object_hash, object_read
from src.objects.tree import tree_checkout, tree_to_dict, index_from_tree
from src.refs import ref_resolve
from src.utils import get_active_branch

def get_target_files(repo,tree,prefix=""):
    target_files = {}
    
    for leaf in tree.items:
        path = os.path.join(prefix, leaf.path)
        obj = object_read(repo, leaf.sha)
        if obj.fmt == b'tree':
            target_files.update(get_target_files(repo, obj, path))
        else:
            target_files[path] = leaf.sha
            
    return target_files
    

def remove_empty_dirs(repo):
    for root, dirs, files in os.walk(repo.worktree, topdown=False):
        if root in (repo.gitdir, repo.worktree):
            continue
        if not dirs and not files:
            try:
                os.rmdir(root)
            except OSError:
                pass
            
            
def is_worktree_clean(repo,index):
    for entry in index.entries:
        path = os.path.join(repo.worktree, entry.name)
        if not os.path.exists(path): #deleted
            return False
        with open(path, "rb") as f:
            sha = object_hash(f, b"blob", None)
            if sha != entry.sha: #modified
                return False
            
    head_sha = ref_resolve(repo, "HEAD")
    if head_sha:
        head_tree = tree_to_dict(repo, "HEAD")
        index_tree = {e.name: e.sha for e in index.entries}
        
        if head_tree != index_tree:
            return False
            
    return True

            

def cmd_switch(args):
    repo = repo_find()
    index = index_read(repo)
    
    target_branch = args.branch
    
    target_sha = ref_resolve(repo, "refs/heads/" + target_branch)
    if not target_sha:
        print(f"Branch {target_branch} does not exist.")
        return
    
    current_branch = get_active_branch(repo)
    
    if current_branch == target_branch:
        print(f"Already on branch '{target_branch}'")
        return
    
    if not is_worktree_clean(repo,index):
        print("Cannot switch branches: you have uncommitted changes.")
        return
    
    commit = object_read(repo, target_sha)
    tree = object_read(repo, commit.kvlm[b'tree'].decode("ascii"))
    target_files = get_target_files(repo,tree)
    
    tracked_files = {e.name for e in index.entries}
    
    for file in target_files.keys():
        full_path = os.path.join(repo.worktree, file)
        
        if os.path.exists(full_path) and file not in tracked_files:
            print(f"Cannot switch branches: Untracked file '{file}' would be overwritten by checkout.")
            return
       
    current_files = {}
    head = ref_resolve(repo, "HEAD")
    if head:
        current_files = tree_to_dict(repo, "HEAD")
        
    for file in current_files.keys():
        full_path = os.path.join(repo.worktree, file)
        if os.path.exists(full_path):
            os.remove(full_path)
            
    remove_empty_dirs(repo)
    
    tree_checkout(repo, tree, repo.worktree)        
    
    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write(f"ref: refs/heads/{target_branch}\n")
        
    index_from_tree(repo,commit.kvlm[b'tree'].decode("ascii"))
    
    print(f"Switched to branch '{target_branch}'")