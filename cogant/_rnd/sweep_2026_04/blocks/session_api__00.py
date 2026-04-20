from cogant import Session

# From local path
session = Session.from_target("./my_repo")

# From URL
session = Session.from_target("https://github.com/user/repo")
