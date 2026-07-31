"""Public surface of the SQLAlchemy database adapter.

Repositories are re-exported here once they exist. Models, the declarative
base, and the engine stay internal — callers outside ``links`` reach this
adapter only through the repository protocols in ``pacts``.
"""
