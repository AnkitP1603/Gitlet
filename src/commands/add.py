def add(repo,paths,delete=True,skip_missing=False):
    rm(repo,paths,delete=False,skip_missing=True)
    
    worktree = repo.worktree+os.sep
    
    clean_paths = set()
    for path in paths:
        abspath = os.path.abspath(path)
        if not abspath.startswith(worktree) or not os.path.isfile(abspath):
            raise Exception(f"Not a file, or outside the worktree: {path}")
        relpath = os.path.relpath(abspath, repo.worktree)
        clean_paths.add((abspath, relpath))
        
    # Find and read the index.  It was modified by rm.  (This isn't
    # optimal, good enough for gitlet!)
    #
    # @FIXME, though: we could just move the index through
    # commands instead of reading and writing it over again.
    index = index_read(repo)
    for (abspath, relpath) in clean_paths:
        with open(abspath, "rb") as f:
            sha = object_hash(f, b"blob", repo)
            
            stat = os.stat(abspath)
            ctime_s = int(stat.st_ctime)
            ctime_ns = stat.st_ctime_ns % 10**9
            mtime_s = int(stat.st_mtime)
            mtime_ns = stat.st_mtime_ns % 10**9
            
            entry = GitIndexEntry(ctime=(ctime_s, ctime_ns), mtime=(mtime_s, mtime_ns), dev=stat.st_dev, ino=stat.st_ino,
                                  mode_type=0b1000, mode_perms=0o644, uid=stat.st_uid, gid=stat.st_gid,
                                  fsize=stat.st_size, sha=sha, flag_assume_valid=False,
                                  flag_stage=False, name=relpath)
            index.entries.append(entry)
            print(f"Added: {relpath}")
            
    index_write(repo, index)