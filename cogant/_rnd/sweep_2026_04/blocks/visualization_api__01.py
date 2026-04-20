from cogant.viz import SemanticVisualizer

sem_viz = SemanticVisualizer()
sem_viz.from_state_space(bundle.state_space_model())
sem_viz.render_html("semantic.html")
