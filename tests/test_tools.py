import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from atlas_core.tools import tool_list_directory

def test_tool_list_directory():
    result = tool_list_directory({"path": "."})
    assert "atlas_core" in result
