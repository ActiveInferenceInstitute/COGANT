# Plugin & Extension API

Related: [Documentation hub](./README.md) · [Architecture](../architecture/README.md) · [Security](../security/README.md)

Guide for extending COGANT with language front-ends, dynamic ingest, normalization, translation, export, validation, and visualization.

Authoritative abstract bases live in [`py/cogant/plugins/base.py`](../py/cogant/plugins/base.py). Each class subclasses `Plugin` and carries [`PluginMetadata`](../py/cogant/plugins/base.py).

