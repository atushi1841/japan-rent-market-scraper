import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import main  # noqa: E402

if __name__ == "__main__":
    asyncio.run(main())
