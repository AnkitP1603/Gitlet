from datetime import datetime
try:
    import grp, pwd
except ModuleNotFoundError:
    pass

import os
import sys

from src.objects.objects import object_read, object_find, object_hash
from src.objects.commit import commit_create
from src.objects.index import index_read
from src.objects.tag import tag_create
from src.objects.tree import ls_tree, tree_checkout, tree_from_index
from src.refs import ref_list, show_ref, ref_resolve, ref_create
from src.ignore import gitignore_read, gitignore_check
from src.status import cmd_status_branch, cmd_status_head_index, cmd_status_index_worktree
from src.cli import argparser
from src.repository import repo_file, repo_find, repo_create
from src.utils import cat_file, log_graphviz, get_active_branch, gitconfig_read, get_gitconfig_user
from src.commands.add import add
from src.commands.rm import rm
from src.commands.switch import cmd_switch

def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)

    match args.command:
        case "add" : cmd_add(args)
        case "cat-file"     : cmd_cat_file(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "checkout"     : cmd_checkout(args)
        case "commit"       : cmd_commit(args)
        case "hash-object"  : cmd_hash_object(args)
        case "init"         : cmd_init(args)
        case "log"          : cmd_log(args)
        case "ls-files"     : cmd_ls_files(args)
        case "ls-tree"      : cmd_ls_tree(args)
        case "rev-parse"    : cmd_rev_parse(args)
        case "rm"           : cmd_rm(args)
        case "show-ref"     : cmd_show_ref(args)
        case "status"       : cmd_status(args)
        case "tag"          : cmd_tag(args)
        case "branch"       : cmd_branch(args)
        case "switch"       : cmd_switch(args)
        case _ : print("Bad command.")

            
def cmd_init(args):
    repo_create(args.path)


def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo,args.object,fmt=args.type.encode())
    
    
def cmd_hash_object(args):
    if args.write:
        repo = repo_find()
    else:
        repo = None
        
    with open(args.path,"rb") as f:
        sha = object_hash(f,args.type.encode(),repo)
        print(sha)
        
        
def cmd_log(args):
    repo = repo_find()
    print("digraph gitlet{")
    print("  node[shape=rect]")
    log_graphviz(repo, object_find(repo, args.commit), set())
    print("}")
    
        
def cmd_ls_tree(args):
    repo = repo_find()
    ls_tree(repo,args.tree,args.recursive)
    

def cmd_checkout(args):
    repo = repo_find()

    obj = object_read(repo, object_find(repo, args.commit))

    if obj.fmt == b'commit':
        obj = object_read(repo, obj.kvlm[b'tree'].decode("ascii"))

    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception(f"Not a directory {args.path}!")
        if os.listdir(args.path):
            raise Exception(f"Not empty {args.path}!")
    else:
        os.makedirs(args.path)

    tree_checkout(repo, obj, os.path.realpath(args.path))
    

def cmd_show_ref(args):
    repo = repo_find()
    refs = ref_list(repo)
    show_ref(repo, refs, prefix="refs")


def cmd_tag(args):
    repo = repo_find()
    
    if args.name:
        tag_create(repo, args.name, args.object, args.create_tag_object)
    else:
        refs = ref_list(repo)
        show_ref(repo, refs["tags"], with_hash=False)
        

def cmd_rev_parse(args):
    if args.type:
        fmt = args.type.encode()
    else:
        fmt = None

    repo = repo_find()

    print(object_find(repo, args.name, fmt, follow=True))
    

def cmd_ls_files(args):
    repo = repo_find()
    index = index_read(repo)
    
    if args.verbose:
        print(f"Index file format v{index.version}, containing {len(index.entries)} entries.")
        
    for e in index.entries:
        print(e.name)
        if args.verbose:
            entry_type = { 0b1000: "regular file",
                           0b1010: "symlink",
                           0b1110: "git link" }[e.mode_type]
            print(f"  {entry_type} with perms: {e.mode_perms:o}")
            print(f"  on blob: {e.sha}")
            print(f"  created: {datetime.fromtimestamp(e.ctime[0])}.{e.ctime[1]}, modified: {datetime.fromtimestamp(e.mtime[0])}.{e.mtime[1]}")
            print(f"  device: {e.dev}, inode: {e.ino}")
            try:
                print(f"  user: {pwd.getpwuid(e.uid).pw_name} ({e.uid})  group: {grp.getgrgid(e.gid).gr_name} ({e.gid})")
            except NameError:
                # These modules are not available on Windows, so just use the less-nice info.
                print(f"  user: {e.uid}  group: {e.gid}")
            print(f"  flags: stage={e.flag_stage} assume_valid={e.flag_assume_valid}")
    

def cmd_check_ignore(args):
    repo = repo_find()
    rules = gitignore_read(repo)
    
    for path in args.path:
        if gitignore_check(rules,path):
            print(path)
            

def cmd_status(args):
    repo = repo_find()
    index = index_read(repo)
    
    cmd_status_branch(repo)
    cmd_status_head_index(repo,index)
    print()
    cmd_status_index_worktree(repo,index)
        
            
def cmd_rm(args):
    repo = repo_find()
    rm(repo, args.path)    


def cmd_add(args):
    repo = repo_find()
    add(repo, args.path)
     

def cmd_commit(args):
    author = get_gitconfig_user(gitconfig_read())
    if not author:
        raise Exception("Configure user.name and user.email first.")
    
    if not args.message:
        raise Exception("Commit message required")

    repo = repo_find()
    index = index_read(repo)
    
    tree = tree_from_index(repo,index)
    
    head = ref_resolve(repo, "HEAD")
    parent = head if head else None
    
    commit = commit_create(repo,
                           tree,
                           parent,
                           author,
                           datetime.now(),
                           args.message)
    
    # Update HEAD so our commit is now the tip of the active branch.
    active_branch = get_active_branch(repo)
    if active_branch: # If we're on a branch, we update refs/heads/BRANCH
        with open(repo_file(repo,"refs","heads",active_branch),"w") as f:
            f.write(commit + "\n")
    else: # Otherwise, we update HEAD itself.
        with open(repo_file(repo,"HEAD"),"w") as f:
            f.write(commit + "\n")
            

def cmd_branch(args):
    repo = repo_find()
    
    if args.name is None:
        refs = ref_list(repo)
        current = get_active_branch(repo)
        
        for branch in refs["heads"].keys():
            if branch == current:
                print(f"* {branch}")
            else:
                print(f"  {branch}")
                
        return

    sha = object_find(repo, "HEAD")
    if ref_resolve(repo, "refs/heads/" + args.name):
        raise Exception(f"Branch {args.name} already exists.")
    
    ref_create(repo, "heads/"+args.name,sha)
