"""Import invariants (manifest §4.1; Art. IV, VI). Guards every later implement run."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "ramp"

NETWORK = {"httpx", "requests", "urllib3", "aiohttp", "openai", "anthropic", "socket", "urllib", "http"}
RULES = {
    # forbidden top-level import -> the only module allowed to use it
    "sqlite3": "store",
    "subprocess": "runner",
    **{lib: "providers" for lib in NETWORK},
}


def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def _files():
    for p in SRC.rglob("*.py"):
        yield p, p.relative_to(SRC).parts[0].removesuffix(".py")


def test_restricted_imports_only_in_owner_module():
    bad = []
    for path, module in _files():
        for imp in _imports(path):
            root = imp.split(".")[0]
            owner = RULES.get(root)
            if owner and owner != module:
                bad.append(f"{path.relative_to(SRC)} imports {imp} (only {owner} may)")
    assert not bad, bad


def test_agents_never_import_store():
    bad = [
        str(p.relative_to(SRC))
        for p, m in _files()
        if m == "agents" and any(i.startswith(("ramp.store", "ramp import store")) for i in _imports(p))
    ]
    assert not bad, bad
