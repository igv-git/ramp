"""Import invariants (manifest §4.1; Art. IV, VI). Guards every later implement run."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "ramp"

NETWORK = {"httpx", "requests", "urllib3", "aiohttp", "openai", "anthropic", "pydantic_ai", "socket",
           "urllib.request", "http.client", "http.server", "ftplib", "smtplib"}
RULES = {
    # forbidden top-level import -> the only module (package) allowed to use it
    "sqlite3": "store",
    "subprocess": "runner",
    **{lib: "providers" for lib in NETWORK},
}
LEAF = {"paths", "config", "models"}  # shared leaf utilities, not modules
NO_STORE = {"agents", "providers", "runner", "lint", "matrix"}


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(SRC.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _imports(path: Path) -> set[str]:
    """Absolute dotted names imported by the file (relative imports resolved)."""
    pkg = _module_name(path).split(".")
    if path.name != "__init__.py":
        pkg = pkg[:-1]
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = pkg[: len(pkg) - (node.level - 1)]
                mod = ".".join(base + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            if mod:
                found.add(mod)
                found |= {f"{mod}.{a.name}" for a in node.names}
    return found


def _files():
    for p in SRC.rglob("*.py"):
        yield p, p.relative_to(SRC).parts[0].removesuffix(".py")


def _importers(prefix: str) -> set[str]:
    """Top-level modules (by name) that import `prefix` or anything under it."""
    out = set()
    for path, module in _files():
        if any(i == prefix or i.startswith(prefix + ".") for i in _imports(path)):
            out.add(module)
    return out


def test_restricted_imports_only_in_owner_module():
    bad = []
    for path, module in _files():
        for imp in _imports(path):
            owner = next((o for k, o in RULES.items() if imp == k or imp.startswith(k + ".")), None)
            if owner and owner != module:
                bad.append(f"{path.relative_to(SRC)} imports {imp} (only {owner} may)")
    assert not bad, bad


def test_leaf_utilities_are_clean():
    bad = []
    for path, module in _files():
        if module in LEAF:
            bad += [f"{path.name}: {i}" for i in _imports(path)
                    if any(i == k or i.startswith(k + ".") for k in RULES)]
    assert not bad, bad


def test_store_not_imported_by_model_facing_modules():
    importers = _importers("ramp.store")
    assert not importers & NO_STORE, importers & NO_STORE


def test_agents_and_gate_do_not_import_providers():
    importers = _importers("ramp.providers")
    assert not importers & {"agents", "gate"}, importers


def test_only_gate_imports_plan_scaffold():
    importers = _importers("ramp.plan.scaffold") - {"plan"}
    assert importers <= {"gate"}, importers


def test_invariant_helper_detects_violations(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("from ramp import store\nimport sqlite3\n")
    # _module_name needs a file under SRC; exercise parsing directly instead
    names = set()
    for node in ast.walk(ast.parse(f.read_text())):
        if isinstance(node, ast.ImportFrom):
            names |= {f"{node.module}.{a.name}" for a in node.names}
    assert "ramp.store" in names
