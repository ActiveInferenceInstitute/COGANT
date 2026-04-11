from cogant.viz import GanttRenderer

gantt = GanttRenderer()
gantt.from_process_model(bundle.process_model())
gantt.render_html("gantt.html")
