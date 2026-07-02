from src.objects.objects import GitObject, object_write

class GitCommit(GitObject):
    fmt = b'commit'
    
    def serialize(self):
        return kvlm_serialize(self.kvlm)
    
    def deserialize(self,data):
        self.kvlm = kvlm_parse(data)
        
    def init(self):
        self.kvlm = dict()
        
        
def kvlm_parse(raw,start=0,dct=None):
    if not dct:
        dct = dict()
        
    space = raw.find(b' ',start)
    newline = raw.find(b'\n',start)
    
    if space<0 or newline<space:
        assert newline==start
        dct[None] = raw[start+1:]
        return dct
    
    key = raw[start:space]
    end = start
    
    while True:
        end = raw.find(b'\n',end+1)
        if raw[end+1]!=ord(' '):
            break
    
    value = raw[space+1:end].replace(b'\n ',b'\n')
    
    if key in dct:
        if type(dct[key])==list:
            dct[key].append(value)
        else:
            dct[key] = [dct[key],value]
    else:
        dct[key] = value
        
    return kvlm_parse(raw,start=end+1,dct=dct)

def kvlm_serialize(kvlm):
    ret = b''
    
    for k in kvlm.keys():
        if k==None:
            continue
        
        val = kvlm[k]
        
        if type(val)!=list:
            val = [val]
        
        for v in val:
            ret += k + b' ' + (v.replace(b'\n',b'\n ')) + b'\n'
            
    ret += b'\n'+kvlm[None]
    
    return ret
            
def commit_create(repo, tree, parent, author, timestamp, message):
    # Note: for the timestamp argument, you must provide a datetime object.
    commit = GitCommit()
    commit.kvlm[b'tree'] = tree.encode("ascii")
    
    if parent:
        commit.kvlm[b'parent'] = parent.encode("ascii")
        
    message = message.strip()+"\n"
    
    offset = int(timestamp.astimezone().utcoffset().total_seconds())
    sign = "+" if offset >= 0 else "-"
    offset = abs(offset)

    tz = f"{sign}{offset // 3600:02}{(offset % 3600) // 60:02}"

    author = f"{author} {int(timestamp.timestamp())} {tz}"
    
    commit.kvlm[b'author'] = author.encode("utf-8")
    commit.kvlm[b'committer'] = author.encode("utf-8")
    commit.kvlm[None] = message.encode("utf-8")
    
    return object_write(commit,repo)