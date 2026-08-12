"""Operator entry point that delegates to :mod:`halls_of_knowledge.cli`.

The script exists so an operator can run ``python scripts/backup_corpus.py``
without remembering the console-script name. All behavior is owned by the
package; this module is intentionally a thin wrapper.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> None:
    from halls_of_knowledge.cli import console

    sys.argv = ["hok", "corpus", "backup", *sys.argv[1:]]
    console()


if __name__ == "__main__":
    main()
