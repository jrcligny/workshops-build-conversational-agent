"""Workshop browser client; no agent or model logic lives here."""

import os
from pathlib import Path

# Also keep configuration local when importing the UI in tests from the repo root.
os.environ.setdefault("CHAINLIT_APP_ROOT", str(Path(__file__).resolve().parents[1]))