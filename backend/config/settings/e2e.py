"""End-to-end tests (`make e2e`): the built app served by Django as in production, with
debug off, over plain HTTP on this machine. The tests write, so they get a database of their
own, seeded afresh on every run.
"""

from .dev import *

DEBUG = False
DATABASES["default"]["NAME"] = "acme_e2e"
# The built app's files, served from where they are, without collectstatic.
WHITENOISE_USE_FINDERS = True
