
from fnmatch import fnmatch
import os

from src.objects.index import index_read
from src.objects.objects import object_read


class GitIgnore(object):
    absolute : list
    scoped : dict
    
    def __init__(self,absolute,scoped):
        self.absolute = absolute
        self.scoped = scoped

def gitignore_parse_helper(raw):
    raw = raw.strip()
    
    if not raw or raw[0] == '#':
        return None
    elif raw[0]=='!':
        return (raw[1:],False)
    elif raw[0]=="\\":
        return (raw[1:],True)
    else:
        return (raw,True)
    
    
def gitignore_parse(lines):
    ret = []
    for line in lines:
        parsed = gitignore_parse_helper(line)
        if parsed:
            ret.append(parsed)
            
    return ret

def gitignore_read(repo):
    ret = GitIgnore(absolute=[],scoped={})
    
    # Read local configuration in .git/info/exclude
    repo_file = os.path.join(repo.gitdir,"info/exclude")
    if os.path.exists(repo_file):
        with open(repo_file,"r") as f:
            ret.absolute.append(gitignore_parse(f.readlines()))
    
    
    # Global configuration
    if "XDG_CONFIG_HOME" in os.environ:
        config_home = os.environ["XDG_CONFIG_HOME"]
    else:
        config_home = os.path.expanduser("~/.config")
    global_file = os.path.join(config_home, "git/ignore")
    
    if os.path.exists(global_file):
        with open(global_file, "r") as f:
            ret.absolute.append(gitignore_parse(f.readlines()))
    
    # .gitignore files in the index
    index = index_read(repo)
    for entry in index.entries:
        if entry.name == ".gitignore" or entry.name.endswith("/.gitignore"):
            dir_name = os.path.dirname(entry.name)
            contents = object_read(repo, entry.sha)
            lines = contents.blobdata.decode("utf8").splitlines()
            ret.scoped[dir_name] = gitignore_parse(lines)
    
    return ret

def check_ignore(rules,path):
    res = None
    for (pattern,include) in rules:
        if fnmatch(path,pattern):
            res = include
    return res

def check_ignore_scoped(rules,path):
    parent = os.path.dirname(path)
    while True:
        if parent in rules:
            res = check_ignore(rules[parent],path)
            if res != None:
                return res
        if parent == "":
            break
        parent = os.path.dirname(parent)
    return None

def check_ignore_absolute(rules,path):
    for ruleset in rules:
        res = check_ignore(ruleset,path)
        if res != None:
            return res
    return False

def gitignore_check(rules,path):
    if os.path.isabs(path):
        raise Exception("This function requires path to be relative to the repository's root")
    
    res = check_ignore_scoped(rules.scoped,path)
    if res != None:
        return res
    return check_ignore_absolute(rules.absolute,path)