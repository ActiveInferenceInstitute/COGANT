# flask_app — Flask-pattern integration fixture

A hand-written snapshot of a realistic Flask + SQLAlchemy application
without actually depending on Flask or SQLAlchemy. All of the
architectural shapes are preserved:

- `config.py` — class hierarchy of ``BaseConfig`` / ``DevelopmentConfig``
  / ``TestingConfig`` / ``ProductionConfig`` with environment overrides.
- `models.py` — descriptor-based field definitions, a dataclass metadata
  block, ``User`` and ``Post`` models, and an in-memory session stand-in.
- `services.py` — DI container, ``UserService`` and ``PostService`` with
  try/except chains and commit/rollback semantics.
- `utils.py` — pagination, slugs, ``retry``/``timed`` decorators, and a
  deep-merge helper.
- `app.py` — application factory, route decorators, middleware chain,
  error handlers, and a dispatcher that ties it all together.

## Why a stub instead of real Flask?

Cloning Flask + its dependencies would (a) inflate the repository, (b)
turn this fixture into a moving target as upstream Flask changes, and
(c) require importable third-party code at analysis time. The stub
captures the ``@app.route`` / ``before_request`` / ``after_request`` /
``errorhandler`` / ``ServiceContainer`` shape that the pipeline's
pattern-matching translation rules care about, without any of those
downsides.
