def rm(repo,paths,delete=True,skip_missing=False):
    index = index_read(repo)
    worktree = repo.worktree+os.sep
    
    abspaths = set()
    
    for path in paths:
        abspath = os.path.abspath(path)
        if abspath.startswith(worktree):
            abspaths.add(abspath)
        else:
            raise Exception(f"{path} is not in the working tree")
        
    kept_entries = []
    removed_entries = []
    
    for e in index.entries:
        full_path = os.path.join(repo.worktree, e.name)
        if full_path in abspaths:
            removed_entries.append(full_path)
            abspaths.remove(full_path)
        else:
            kept_entries.append(e)
            
    if len(abspaths) > 0 and not skip_missing:
        raise Exception(f"Cannot remove paths not in the index: {abspaths}")
       
    if delete:
        for path in removed_entries:
            os.unlink(path)
            
    index.entries = kept_entries
    index_write(repo, index)