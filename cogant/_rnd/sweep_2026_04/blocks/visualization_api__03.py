from cogant.viz import DiffVisualizer

diff = DiffVisualizer(bundle1_data, bundle2_data)
diff.render_html("diff.html")
diff_json = diff.render_json()
