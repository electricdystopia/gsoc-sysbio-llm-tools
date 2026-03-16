from fastmcp import FastMCP
import requests

mcp = FastMCP("cytoscape")
CYTOSCAPE_URL = "http://localhost:1234/v1"

@mcp.tool()
def get_network_list() -> list:
    """List all networks currently open in Cytoscape."""
    resp = requests.get(f"{CYTOSCAPE_URL}/networks")
    return resp.json()

@mcp.tool()
def apply_layout(network_id: int, layout: str = "force-directed") -> dict:
    """Apply a layout algorithm to a network."""
    resp = requests.get(
        f"{CYTOSCAPE_URL}/apply/layouts/{layout}/{network_id}"
    )
    return {"status": resp.status_code}

if __name__ == "__main__":
    mcp.run(transport="http", port=8000)