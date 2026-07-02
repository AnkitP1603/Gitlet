


import os

from src.objects.index import GitIndex, GitIndexEntry, index_write
from src.objects.objects import GitObject, object_read, object_find, object_write


class GitTreeLeaf(object):
    def __init__(self,mode,path,sha):
        self.mode = mode
        self.path = path
        self.sha = sha
        
class GitTree(GitObject):
    fmt = b'tree'
    
    def serialize(self):
        return tree_serialize(self)
    
    def deserialize(self,data):
        self.items = tree_parse(data)
    
    def init(self):
        self.items = list()
        
        
def tree_parse_helper(raw,start=0):
    x = raw.find(b' ',start)
    assert x-start==5 or x-start==6
    
    mode = raw[start:x]
    
    if len(mode)==5:
        mode = b'0'+mode
        
    y = raw.find(b'\x00',x)
    
    path = raw[x+1:y]
    
    raw_sha = int.from_bytes(raw[y+1:y+21],"big")
    
    sha = format(raw_sha,"040x")
    return y+21,GitTreeLeaf(mode,path.decode("utf-8"),sha)
    
    
def tree_parse(raw):
    pos = 0
    max = len(raw)
    ret = list()
    
    while pos<max:
        pos,leaf = tree_parse_helper(raw,pos)
        ret.append(leaf)
        
    return ret

def tree_leaf_sort_key(leaf):
    if leaf.mode.startswith(b"4"):
        return leaf.path+'/'
    else:
        return leaf.path
    
def tree_serialize(obj):
    obj.items.sort(key=tree_leaf_sort_key)
    ret = b''
    for i in obj.items:
        ret += i.mode
        ret += b' '
        ret += i.path.encode("utf8")
        ret += b'\x00'
        sha = int(i.sha, 16)
        ret += sha.to_bytes(20, byteorder="big")
    
    return ret


def ls_tree(repo,ref,recursive=None,prefix=""):
    sha = object_find(repo,ref,fmt=b'tree',follow=True)
    
    obj = object_read(repo,sha)
    
    for item in obj.items:
        if len(item.mode)==5:
            type = item.mode[0:1]
        else:
            type = item.mode[0:2]
            
        match type:
            case b'04': type = "tree"
            case b'10': type = "blob" # A regular file.
            case b'12': type = "blob" # A symlink. Blob contents is link target.
            case b'16': type = "commit" # A submodule
            case _: raise Exception(f"Weird tree leaf mode {item.mode}")
            
        if not recursive or type!="tree":
            print(f"{'0' * (6 - len(item.mode)) + item.mode.decode('ascii')} {type} {item.sha}\t{os.path.join(prefix, item.path)}")
        else:
            ls_tree(repo,item.sha,recursive,prefix=os.path.join(prefix,item.path))
        
def tree_checkout(repo, tree, path):
    for item in tree.items:
        obj = object_read(repo, item.sha)
        dest = os.path.join(path, item.path)

        if obj.fmt == b'tree':
            os.makedirs(dest, exist_ok=True)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b'blob':
            # @TODO Support symlinks (identified by mode 12****)
            with open(dest, 'wb') as f:
                f.write(obj.blobdata)
                
                
def tree_to_dict(repo,ref,prefix=""):
    ret = {}
    tree_sha = object_find(repo,ref,fmt=b'tree',follow=True)
    # print(f"tree_sha: {tree_sha}")
    tree = object_read(repo,tree_sha)
    
    for leaf in tree.items:
        full_path = os.path.join(prefix, leaf.path)
        
        # We read the object to extract its type (this is uselessly expensive: we could just open it as a file and read the first few bytes)
        is_subtree = leaf.mode.startswith(b'04')
        
        if is_subtree:
            ret.update(tree_to_dict(repo, leaf.sha, prefix=full_path))
        else:
            ret[full_path] = leaf.sha
            
    return ret


def tree_from_index(repo,index):
    contents = {}
    contents[""] = []
    
    for entry in index.entries:
        dirname = os.path.dirname(entry.name)
        
        # We create all dictonary entries up to root ("").  We need
        # them *all*, because even if a directory holds no files it
        # will contain at least a tree.
        key = dirname
        while key!="":
            if not key in contents:
                contents[key] = []
            key = os.path.dirname(key)
            
        contents[dirname].append(entry)
        
    sorted_dirs = sorted(contents.keys(), key=len, reverse=True)
    sha = None
    
    for path in sorted_dirs:
        tree = GitTree()
        
        for entry in contents[path]:
            if isinstance(entry, GitIndexEntry): # Regular entry (a file)
                leaf_mode = f"{entry.mode_type:02o}{entry.mode_perms:04o}".encode("ascii")
                leaf = GitTreeLeaf(mode = leaf_mode, path=os.path.basename(entry.name), sha=entry.sha)
            else: # Tree.  We've stored it as a pair: (basename, SHA)
                leaf = GitTreeLeaf(mode = b"040000", path=entry[0], sha=entry[1])
                
            tree.items.append(leaf)
            
        sha = object_write(tree,repo)
        
        parent = os.path.dirname(path)
        base = os.path.basename(path) # The name without the path, eg main.go for src/main.go
        contents[parent].append((base,sha))
        
    return sha


def index_from_tree(repo,tree_sha):
    entries = []
    
    walk_tree(repo, tree_sha, "", entries)
    
    index = GitIndex(version=2, entries=entries)
    index_write(repo, index)
    
    
def walk_tree(repo, tree_sha, prefix, entries):
    tree = object_read(repo, tree_sha)
    for leaf in tree.items:
        path = os.path.join(prefix, leaf.path)
        
        if leaf.mode.startswith(b"04"):
            walk_tree(repo, leaf.sha, path, entries)
        else:
            stat = os.stat(os.path.join(repo.worktree, path))
            ctime_s = int(stat.st_ctime)
            ctime_ns = stat.st_ctime_ns % 10**9
            mtime_s = int(stat.st_mtime)
            mtime_ns = stat.st_mtime_ns % 10**9
            
            entry = GitIndexEntry(
                ctime=(ctime_s, ctime_ns),
                mtime=(mtime_s, mtime_ns),
                dev=stat.st_dev,
                ino=stat.st_ino,
                mode_type = int(leaf.mode[:2], 8),
                mode_perms = int(leaf.mode[2:], 8),
                uid=stat.st_uid,
                gid=stat.st_gid,
                fsize=stat.st_size,
                sha=leaf.sha,
                flag_assume_valid=False,
                flag_stage=0,
                name=path
            )
            entries.append(entry)