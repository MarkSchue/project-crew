"""Package marker for agent_platform.migrations.

Migration files are named ``NNNN_description.py`` and expose ``up()`` and
``down()``. ``mas project migrate`` runs pending migrations against a
target project directory (plan milestone M1.7/M1.9). Migrations are
ordered by their numeric prefix.
"""
