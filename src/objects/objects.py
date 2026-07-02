import hashlib, os, zlib, re
from src.refs import ref_resolve
from src.repository import repo_dir, repo_file
from src.objects.commit import GitCommit
from src.objects.tree import GitTree
from src.objects.blob import GitBlob
from src.objects.tag import GitTag

class GitObject(object):
    def __init__(self,data=None):
        if data != None:
            self.deserialize(data)
        else:
            self.init()
            
    def serialize(self):
        """This function MUST be implemented by subclasses."""
        raise Exception("Unimplemented!")
    
    def deserialize(self,data):
        """This function MUST be implemented by subclasses."""
        raise Exception("Unimplemented!")
    
    def init(self):
        pass

def object_read(repo,sha):
    """Read object sha from Git repository repo.  Return a
    GitObject whose exact type depends on the object."""
    
    path = repo_file(repo,"objects",sha[0:2],sha[2:])
    
    if not os.path.isfile(path):
        return None
    
    with open(path,"rb") as f:
        raw = zlib.decompress(f.read())
        
        x = raw.find(b' ')
        fmt = raw[0:x]
        
        y = raw.find(b'\x00',x)
        size = int(raw[x:y].decode("ascii"))
        
        if size!=len(raw)-y-1:
            raise Exception(f"Malformed object {sha}: bad length")
        
        match fmt:
            case b'commit': c = GitCommit
            case b'tree': c = GitTree
            case b'blob': c = GitBlob
            case b'tag': c = GitTag
            case _: raise Exception(f"Unknown type {fmt.decode('ascii')} for object {sha}")
            
        return c(raw[y+1:])
        
def object_write(obj, repo=None):
    """Write object obj to Git repository repo. Return the sha as a
    string."""
    
    data = obj.serialize()
    res = (obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data)
    sha = hashlib.sha1(res).hexdigest()
    
    if repo:
        path = repo_file(repo,"objects",sha[0:2],sha[2:],mkdir=True)
        
        if not os.path.isfile(path):
            with open(path,"wb") as f:
                f.write(zlib.compress(res))
        
    return sha




def object_find(repo,name,fmt=None,follow=False):
    """Find object named name in repo, optionally requiring it to be of type fmt and return its sha"""
    sha = object_resolve(repo,name)
    
    if not sha:
        raise Exception(f"No such reference {name}.")
    
    if len(sha)>1:
        raise Exception(f"Ambiguous reference {name}: Candidates are:\n - {'\n - '.join(sha)}.")
    
    sha = sha[0]
    
    if not fmt:
        return sha
    
    while True:
        obj = object_read(repo,sha)
        
        # print(f"object {sha} is a {obj.fmt.decode('ascii')}")
        
        if obj.fmt == fmt:
            return sha
        
        if not follow:
            return None
        
        if obj.fmt == b'tag':
            sha = obj.kvlm[b'object'].decode("ascii")
        elif obj.fmt == b'commit' and fmt==b'tree':
            sha = obj.kvlm[b'tree'].decode("ascii")
        else:
            return None 


def object_hash(file,fmt,repo=None):
    data = file.read()
    
    match fmt:
        case b'commit': obj = GitCommit(data)
        case b'tree': obj = GitTree(data)
        case b'blob': obj = GitBlob(data)
        case b'tag': obj = GitTag(data)
        case _: raise Exception(f"Unknown type {fmt.decode('ascii')}")
        
    return object_write(obj,repo)


def object_resolve(repo, name):
    """
    Resolve name to an object hash in repo.
        This function is aware of:
            - the HEAD literal
            - short and long hashes
            - tags
            - branches
            - remote branches
    """
    
    candidates = []
    hashRE = re.compile(r"^[0-9A-Fa-f]{4,40}$")
    
    if not name.strip():
        return None
    
    if name=="HEAD":
        head = ref_resolve(repo,"HEAD")
        # print(f"HEAD resolves to {head}")
        return [head] if head else []
    
    if hashRE.match(name):
        name = name.lower()
        prefix = name[0:2]
        
        path = repo_dir(repo,"objects",prefix,mkdir=False)
        
        if path:
            rem = name[2:]
            for f in os.listdir(path):
                if f.startswith(rem):
                    candidates.append(prefix+f)
                    
    as_tag = ref_resolve(repo,"refs/tags/"+name)
    if as_tag:
        candidates.append(as_tag)
        
    as_branch = ref_resolve(repo,"refs/heads/"+name)
    if as_branch:
        candidates.append(as_branch)
        
    as_remote_branch = ref_resolve(repo,"refs/remotes/"+name)
    if as_remote_branch:
        candidates.append(as_remote_branch)
        
    return candidates
    
    