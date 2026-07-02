import argparse

argparser = argparse.ArgumentParser(description="Gitlet - a simple version control system")

argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True

argsp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")
argsp.add_argument("path", metavar="directory", nargs="?", default=".", help="Where to create the repository.")

argsp = argsubparsers.add_parser("cat-file", help="Provide content of repository objects")
argsp.add_argument("type", metavar="type",choices = ["commit", "tree", "blob", "tag"], help="Specify the type")
argsp.add_argument("object", metavar="object", help="The sha of the object to display")

argsp = argsubparsers.add_parser("hash-object",help="Compute object ID and optionally creates a blob from a file")
argsp.add_argument("-t", metavar="type", dest="type", choices=["blob", "commit", "tag", "tree"], default="blob", help="Specify the type")
argsp.add_argument("-w", dest="write", action="store_true", help="Actually write the object into the database")
argsp.add_argument("path", metavar="path", help="Read object from <file>")

argsp = argsubparsers.add_parser("log", help="Display history of commits")
argsp.add_argument("commit", default="HEAD", nargs="?", help="The commit to start from (default: HEAD)")

argsp = argsubparsers.add_parser("ls-tree", help="Pretty-print a tree object")
argsp.add_argument("-r",dest="recursive",action="store_true",help="Recurse into sub-trees")
argsp.add_argument("tree",help="The tree-ish object")

argsp = argsubparsers.add_parser("checkout", help="Checkout a commit inside of a directory.")
argsp.add_argument("commit",help="The commit or tree to checkout.")
argsp.add_argument("path",help="The EMPTY directory to checkout on.")

argsp = argsubparsers.add_parser("show-ref", help="List references.")

argsp = argsubparsers.add_parser("tag", help="List and create tags")
argsp.add_argument("-a", action="store_true", dest="create_tag_object", help="Whether to create a tag object")
argsp.add_argument("name", nargs="?", help="The new tag's name")
argsp.add_argument("object", default="HEAD", nargs="?", help="The object the new tag will point to")

argsp = argsubparsers.add_parser("rev-parse", help="Parse revision (or other objects) identifiers")
argsp.add_argument("-type",
                   metavar="type",
                   dest="type",
                   choices=["blob", "commit", "tag", "tree"],
                   default=None,
                   help="Specify the expected type")
argsp.add_argument("name", help="The name to parse")

argsp = argsubparsers.add_parser("ls-files", help="List all the stage files")
argsp.add_argument("--verbose",action="store_true",help="Show everything")

argsp = argsubparsers.add_parser("check-ignore", help="Check path(s) against ignore rules.")
argsp.add_argument("path",nargs="+",help="The path(s) to check")

argsp = argsubparsers.add_parser("status", help="Show the working tree status")

argsp = argsubparsers.add_parser("rm", help="Remove files from the working tree and the index.")
argsp.add_argument("path", nargs="+", help="Files to remove")

argsp = argsubparsers.add_parser("add", help = "Add files contents to the index.")
argsp.add_argument("path", nargs="+", help="Files to add")

argsp = argsubparsers.add_parser("commit", help="Record changes to the repository.")
argsp.add_argument("-m",
                   metavar="message",
                   dest="message",
                   help="Message to associate with this commit.")

argsp = argsubparsers.add_parser("branch", help="List or create branches.")
argsp.add_argument("name", nargs="?", help="The name of the new branch to create.")

arsgp = argsubparsers.add_parser("switch", help="Switch branches.")
arsgp.add_argument("branch", help="The name of the branch to switch to.")

