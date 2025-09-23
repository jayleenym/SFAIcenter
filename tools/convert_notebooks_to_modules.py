import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
import fnmatch
import json
import ast


def sanitize_module_name(name: str) -> str:
    base = re.sub(r"[^0-9a-zA-Z_]+", "_", name)
    if not base:
        base = "notebook_module"
    if base[0].isdigit():
        base = f"nb_{base}"
    return base.lower()


def is_name_only_targets(targets: List[ast.expr]) -> bool:
    def is_name(expr: ast.expr) -> bool:
        if isinstance(expr, ast.Name):
            return True
        if isinstance(expr, (ast.Tuple, ast.List)):
            return all(is_name(elt) for elt in expr.elts)
        return False

    return all(is_name(t) for t in targets)


def is_simple_literal(node: ast.AST) -> bool:
    if isinstance(node, (ast.Constant,)):
        return True
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(is_simple_literal(elt) for elt in node.elts)
    if isinstance(node, ast.Dict):
        return all(
            (k is None or is_simple_literal(k)) and is_simple_literal(v)
            for k, v in zip(node.keys, node.values)
        )
    # Allow simple named constants like True/False/None as ast.NameConstant on older versions
    if hasattr(ast, "NameConstant") and isinstance(node, getattr(ast, "NameConstant")):
        return True
    return False


def remove_ipython_magics(code: str) -> str:
    cleaned_lines: List[str] = []
    for line in code.splitlines():
        stripped = line.lstrip()
        if not stripped:
            cleaned_lines.append(line)
            continue
        if stripped.startswith("%") or stripped.startswith("!"):
            continue
        if "get_ipython(" in stripped:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def extract_module_elements(source_code: str) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Return (imports, constants, functions, classes) as source code strings in original order."""
    module = ast.parse(source_code)
    imports: List[str] = []
    constants: List[str] = []
    functions: List[str] = []
    classes: List[str] = []

    def get_src(node: ast.AST) -> Optional[str]:
        try:
            segment = ast.get_source_segment(source_code, node)
            if segment is not None:
                return segment
        except Exception:
            pass
        # Fallback to unparse if available
        if hasattr(ast, "unparse"):
            try:
                return ast.unparse(node)  # type: ignore[attr-defined]
            except Exception:
                return None
        return None

    for node in module.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            src = get_src(node)
            if src:
                imports.append(src)
            continue

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            src = get_src(node)
            if src:
                functions.append(src)
            continue

        if isinstance(node, ast.ClassDef):
            src = get_src(node)
            if src:
                classes.append(src)
            continue

        if isinstance(node, ast.Assign):
            if is_name_only_targets(node.targets) and is_simple_literal(node.value):
                src = get_src(node)
                if src:
                    constants.append(src)
            continue

        if isinstance(node, ast.AnnAssign):
            target_is_name = isinstance(node.target, ast.Name)
            value_ok = (node.value is None) or is_simple_literal(node.value)
            if target_is_name and value_ok:
                src = get_src(node)
                if src:
                    constants.append(src)
            continue

        # Ignore everything else: top-level code, if __name__ == '__main__', etc.

    return imports, constants, functions, classes


def load_notebook_code(notebook_path: Path) -> str:
    with notebook_path.open("r", encoding="utf-8") as f:
        nb = json.load(f)
    cells = nb.get("cells", [])
    pieces: List[str] = []
    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        cell_src = cell.get("source", "")
        if isinstance(cell_src, list):
            cell_src = "".join(cell_src)
        if not isinstance(cell_src, str):
            continue
        cleaned = remove_ipython_magics(cell_src)
        if cleaned.strip():
            pieces.append(cleaned)
    return "\n\n".join(pieces)


def build_module_source(nb_path: Path, module_name: str) -> str:
    raw_code = load_notebook_code(nb_path)
    imports, constants, functions, classes = extract_module_elements(raw_code)

    unique_imports: List[str] = []
    seen = set()
    for imp in imports:
        if imp not in seen:
            seen.add(imp)
            unique_imports.append(imp)

    exports: List[str] = []
    exported_names: List[str] = []

    # Collect names from simple constant assignments
    for const_stmt in constants:
        try:
            node = ast.parse(const_stmt).body[0]
            names: List[str] = []
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        names.append(tgt.id)
                    elif isinstance(tgt, (ast.Tuple, ast.List)):
                        for elt in tgt.elts:
                            if isinstance(elt, ast.Name):
                                names.append(elt.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.append(node.target.id)
            exported_names.extend(names)
        except Exception:
            pass

    def collect_def_names(blocks: List[str]) -> List[str]:
        result: List[str] = []
        for src in blocks:
            try:
                node = ast.parse(src).body[0]
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    result.append(node.name)
            except Exception:
                pass
        return result

    exported_names.extend(collect_def_names(functions))
    exported_names.extend(collect_def_names(classes))

    lines: List[str] = []
    lines.append("# Generated from notebook: {}".format(nb_path.name))
    lines.append("# This file was auto-created to expose reusable code as a module.")
    if unique_imports:
        lines.append("")
        lines.extend(unique_imports)
    if constants:
        lines.append("")
        lines.extend(constants)
    if classes:
        lines.append("")
        lines.extend(classes)
    if functions:
        lines.append("")
        lines.extend(functions)

    if exported_names:
        unique_exported = sorted(set(exported_names))
        lines.append("")
        all_line = "__all__ = [" + ", ".join(repr(n) for n in unique_exported) + "]"
        lines.append(all_line)

    return "\n".join(lines) + "\n"


def find_notebooks(start_dir: Path) -> List[Path]:
    return sorted(p for p in start_dir.rglob("*.ipynb") if ".ipynb_checkpoints" not in str(p))


def convert_notebooks(
    notebooks: Iterable[Path], output_dir: Path, overwrite: bool = True
) -> List[Tuple[Path, Path]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Tuple[Path, Path]] = []
    for nb_path in notebooks:
        module_name = sanitize_module_name(nb_path.stem)
        target_path = output_dir / f"{module_name}.py"
        if target_path.exists() and not overwrite:
            continue
        try:
            module_src = build_module_source(nb_path, module_name)
        except Exception as exc:
            sys.stderr.write(f"[WARN] Failed to convert {nb_path}: {exc}\n")
            continue
        target_path.write_text(module_src, encoding="utf-8")
        results.append((nb_path, target_path))
    return results


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Convert .ipynb notebooks to Python modules")
    parser.add_argument(
        "--root",
        type=str,
        default=str(Path.cwd()),
        help="Project root to search for notebooks (default: CWD)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path("src/notebook_modules")),
        help="Output directory for generated modules",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Do not overwrite existing .py files",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help=(
            "Exclude notebooks by name, stem, or glob pattern. Can be specified multiple times."
        ),
    )

    args = parser.parse_args(argv)
    start_dir = Path(args.root).resolve()
    out_dir = Path(args.out).resolve()
    overwrite = not args.no_overwrite

    notebooks = find_notebooks(start_dir)
    if args.exclude:
        patterns: List[str] = list(args.exclude)
        def is_excluded(p: Path) -> bool:
            full = str(p)
            name = p.name
            stem = p.stem
            for pat in patterns:
                if stem == pat or name == pat:
                    return True
                if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(full, pat):
                    return True
            return False

        notebooks = [p for p in notebooks if not is_excluded(p)]
    if not notebooks:
        print("No notebooks found.")
        return 0

    results = convert_notebooks(notebooks, out_dir, overwrite)
    if not results:
        print("No modules generated.")
        return 0

    print("Generated modules:")
    for nb_path, py_path in results:
        rel_nb = os.path.relpath(str(nb_path), str(start_dir))
        rel_py = os.path.relpath(str(py_path), str(start_dir))
        print(f" - {rel_nb} -> {rel_py}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

