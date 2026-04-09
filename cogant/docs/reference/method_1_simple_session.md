## Method 1: Simple Session
session = Session.from_target("./my_repo")
session.extract_static()
session.build_graph()
session.translate_to_gnn()
session.export_all("output/")

