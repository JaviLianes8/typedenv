"""Allow ``python -m typedenv`` as an alias for the ``typedenv`` command."""

import sys

from ._cli import main

sys.exit(main())
