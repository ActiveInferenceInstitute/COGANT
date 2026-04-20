from cogant.viz import HTMLSiteRenderer
import json

bundle_data = json.loads(bundle.to_json())
renderer = HTMLSiteRenderer(bundle_data)
index_path = renderer.render("html_site/")
