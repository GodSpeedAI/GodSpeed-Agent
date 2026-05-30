from mcp.cybernetic_nav_server.server import TOOL_NAMES, call_tool


def main() -> int:
	from mcp.cybernetic_nav_server.server import main as _main

	return _main()

__all__ = ["TOOL_NAMES", "call_tool"]


if __name__ == "__main__":
	raise SystemExit(main())

