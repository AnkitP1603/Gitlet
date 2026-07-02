import sys, os
from src.objects.objects import object_hash, object_read, object_find
from src.objects.tree import tree_to_dict
from src.refs import ref_resolve
from src.repository import repo_file
import configparser



def cat_file(repo,sha,fmt=None):
    obj = object_read(repo,object_find(repo,sha,fmt=fmt,follow=True))
    print("object {}: type {}, size {}".format(sha, obj.fmt.decode("ascii"), len(obj.serialize())))
    sys.stdout.buffer.write(obj.serialize())
    
def log_graphviz(repo, sha, seen):
    if sha in seen:
        return
    
    seen.add(sha)
    commit = object_read(repo,sha)
    
    message = commit.kvlm[None].decode("utf-8").strip()
    message = message.replace("\\","\\\\")
    message = message.replace("\"","\\\"")
    
    if '\n' in message:
        message = message.split("\n")[0] + "..."
        
    print(f"  c_{sha} [label=\"{sha[0:7]}: {message}\"]")
    assert commit.fmt == b'commit'
    
    if not b'parent' in commit.kvlm.keys():
        return
    
    parents = commit.kvlm[b'parent']
    
    if type(parents)!=list:
        parents = [parents]
        
    for p in parents:
        p = p.decode("ascii")
        print(f"  c_{sha} -> c_{p};")
        log_graphviz(repo, p, seen)
        
        
def get_active_branch(repo):
    with open(repo_file(repo,"HEAD"),"r") as f:
        head = f.read()
        
    if head.startswith("ref: refs/heads/"):
        return head[16:-1]
    else:
        return False
    
    
def gitconfig_read():
    xdg_config_home = os.environ["XDG_CONFIG_HOME"] if "XDG_CONFIG_HOME" in os.environ else "~/.config"
    configfiles = [
        os.path.expanduser(os.path.join(xdg_config_home, "git/config")),
        os.path.expanduser("~/.gitconfig")
    ]

    config = configparser.ConfigParser()
    config.read(configfiles)
    return config

def get_gitconfig_user(config):
    if "user" in config:
        if "name" in config["user"] and "email" in config["user"]:
            return f"{config['user']['name']} <{config['user']['email']}>"
    return None




