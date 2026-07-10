"""Business logic: generate markdown inputs, then time each implementation.

No typer / rich / pydantic imports. Receives the config object by duck typing and
returns plain dataclasses for the CLI to render.
"""

from __future__ import annotations

import random
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .exceptions import BenchError

if TYPE_CHECKING:  # type-only
    from .config_models import BenchConfig


# --- markdown generation --------------------------------------------------

_LOREM = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua enim ad minim veniam quis nostrud "
    "exercitation ullamco laboris nisi aliquip ex ea commodo consequat duis aute irure "
    "reprehenderit voluptate velit esse cillum fugiat nulla pariatur excepteur sint "
    "occaecat cupidatat non proident sunt culpa qui officia deserunt mollit anim id est"
).split()


class _Gen:
    """Random-but-valid markdown with a mix of block/inline features. No raw HTML."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.words = 0

    def _words(self, n: int) -> str:
        self.words += n
        return " ".join(self.rng.choice(_LOREM) for _ in range(n))

    def _sentence(self) -> str:
        parts = self._words(self.rng.randint(6, 16)).split()
        for i, p in enumerate(parts):
            r = self.rng.random()
            if r < 0.05:
                parts[i] = f"**{p}**"
            elif r < 0.09:
                parts[i] = f"*{p}*"
            elif r < 0.12:
                parts[i] = f"`{p}`"
            elif r < 0.14:
                parts[i] = f"[{p}](https://example.com/{p})"
        return " ".join(parts).capitalize() + "."

    def _paragraph(self) -> str:
        return " ".join(self._sentence() for _ in range(self.rng.randint(2, 5)))

    def _heading(self) -> str:
        return "#" * self.rng.randint(1, 3) + " " + self._words(self.rng.randint(2, 6)).title()

    def _bullets(self) -> str:
        lines = []
        for _ in range(self.rng.randint(3, 6)):
            lines.append("- " + self._sentence())
            if self.rng.random() < 0.25:
                lines.append("  - " + self._sentence())
        return "\n".join(lines)

    def _ordered(self) -> str:
        return "\n".join(f"{i + 1}. " + self._sentence() for i in range(self.rng.randint(3, 6)))

    def _table(self) -> str:
        cols = self.rng.randint(2, 4)
        header = [self._words(self.rng.randint(1, 2)).title() for _ in range(cols)]
        aligns = [self.rng.choice([":--", "--:", ":-:", "---"]) for _ in range(cols)]
        rows = ["| " + " | ".join(self._words(self.rng.randint(1, 3)) for _ in range(cols)) + " |"
                for _ in range(self.rng.randint(2, 5))]
        return "| " + " | ".join(header) + " |\n| " + " | ".join(aligns) + " |\n" + "\n".join(rows)

    def _code(self) -> str:
        lang = self.rng.choice(["", "py", "js", "text", "sh"])
        body = "\n".join(self._words(self.rng.randint(3, 8)) for _ in range(self.rng.randint(4, 12)))
        return f"```{lang}\n{body}\n```"

    def _quote(self) -> str:
        return "\n".join("> " + self._sentence() for _ in range(self.rng.randint(1, 3)))

    def build(self, target_words: int) -> str:
        blocks = ["# " + self._words(self.rng.randint(3, 6)).title()]
        pickers = [
            self._paragraph, self._paragraph, self._paragraph,
            self._heading, self._bullets, self._ordered, self._table, self._code, self._quote,
        ]
        while self.words < target_words:
            blocks.append(self.rng.choice(pickers)())
            if self.rng.random() < 0.06:
                blocks.append(self.rng.choice(["---", "***"]))
        return "\n\n".join(blocks) + "\n"


# --- result types ---------------------------------------------------------

@dataclass
class ImplResult:
    name: str
    ok: bool
    total_seconds: float = 0.0
    error: Optional[str] = None


@dataclass
class ClassResult:
    name: str
    files: int
    total_bytes: int
    total_words: int
    results: list[ImplResult] = field(default_factory=list)


@dataclass
class BenchOutput:
    classes: list[ClassResult]
    impl_names: list[str]
    gen_seconds: float
    output_dir: Path
    words_per_page: int


# --- helpers --------------------------------------------------------------

def resolve_repo_root(hint: Optional[str]) -> Path:
    """Find the md2docx repo root (contains js/src/index.js). Walk up from `hint`
    or the cwd. Explicit hint that isn't valid is an error."""
    def is_root(p: Path) -> bool:
        return (p / "js" / "src" / "index.js").exists()

    if hint:
        p = Path(hint).expanduser().resolve()
        if is_root(p):
            return p
        raise BenchError(f"repo_root {p} does not look like the md2docx repo (no js/src/index.js).")

    for base in (Path.cwd(), *Path.cwd().parents):
        if is_root(base):
            return base
    raise BenchError("Could not locate the md2docx repo root; set repo_root in the config.")


def discover_impls(cfg: "BenchConfig", repo_root: Path) -> list[tuple[str, list[str]]]:
    """Available (name, argv-template) pairs. Templates use {in}/{out}/{dir}."""
    node = shutil.which("node")
    pandoc = shutil.which("pandoc")
    js_cli = repo_root / "js" / "src" / "index.js"
    py_full = repo_root / "python" / ".venv" / "bin" / "md2docx"
    py_lite = repo_root / "python" / ".venv" / "bin" / "md2docx-lite"
    ref = repo_root / "pandoc" / "references" / "circeus-light.docx"

    candidates: list[tuple[str, list[str]]] = []
    if node and js_cli.exists():
        candidates.append(("js", [node, str(js_cli), "{in}", "-o", "{out}"]))
    if py_full.exists():
        candidates.append(("python", [str(py_full), "convert", "{in}", "-o", "{out}", "-q"]))
    if py_lite.exists():
        candidates.append(("python-lite", [str(py_lite), "{in}", "-o", "{out}", "-q"]))
    if pandoc and ref.exists():
        candidates.append(("pandoc", [pandoc, "{in}", "-o", "{out}",
                                      "--reference-doc", str(ref), "--resource-path", "{dir}"]))

    wanted = cfg.implementations
    if wanted:
        by_name = dict(candidates)
        missing = [w for w in wanted if w not in by_name]
        if missing:
            raise BenchError(f"requested implementations unavailable: {missing} "
                             f"(available: {sorted(by_name)})")
        return [(w, by_name[w]) for w in wanted]
    return candidates


def _fill(tmpl: list[str], src: Path, out: Path) -> list[str]:
    return [a.replace("{in}", str(src)).replace("{out}", str(out)).replace("{dir}", str(src.parent))
            for a in tmpl]


def _run_one(argv: list[str]) -> bool:
    return subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def _generate(cfg: "BenchConfig") -> dict[str, list[Path]]:
    inputs_root = Path(cfg.inputs_dir)
    out: dict[str, list[Path]] = {}
    for sc in cfg.sizes:
        cls_dir = inputs_root / sc.name
        cls_dir.mkdir(parents=True, exist_ok=True)
        target = int(sc.pages * cfg.words_per_page)
        files = []
        for i in range(sc.count):
            gen = _Gen(random.Random(sc.seed * 100_000 + i))
            path = cls_dir / f"{sc.name}-{i:03d}.md"
            path.write_text(gen.build(target), encoding="utf-8")
            files.append(path)
        out[sc.name] = files
    return out


def _discover_inputs(cfg: "BenchConfig") -> dict[str, list[Path]]:
    inputs_root = Path(cfg.inputs_dir)
    out: dict[str, list[Path]] = {}
    for sc in cfg.sizes:
        files = sorted((inputs_root / sc.name).glob("*.md"))
        if not files:
            raise BenchError(f"no inputs for class '{sc.name}' in {inputs_root / sc.name} "
                             f"(enable regenerate).")
        out[sc.name] = files
    return out


# --- entry point ----------------------------------------------------------

def run(cfg: "BenchConfig", *, dry_run: bool = False) -> BenchOutput:
    repo_root = resolve_repo_root(cfg.repo_root)
    impls = discover_impls(cfg, repo_root)
    if not impls:
        raise BenchError("no implementations available to benchmark (run ./setup.sh).")

    if dry_run:
        return BenchOutput(classes=[], impl_names=[n for n, _ in impls], gen_seconds=0.0,
                           output_dir=Path(cfg.output_dir), words_per_page=cfg.words_per_page)

    gen_seconds = 0.0
    if cfg.regenerate:
        t0 = time.perf_counter()
        inputs = _generate(cfg)
        gen_seconds = time.perf_counter() - t0
    else:
        inputs = _discover_inputs(cfg)

    out_dir = Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if cfg.warmup:
        warm = next((f for files in inputs.values() for f in files), None)
        if warm:
            for _, tmpl in impls:
                _run_one(_fill(tmpl, warm, out_dir / "warmup.docx"))

    classes: list[ClassResult] = []
    for sc in cfg.sizes:
        files = inputs[sc.name]
        total_bytes = sum(f.stat().st_size for f in files)
        total_words = sum(len(f.read_text(encoding="utf-8").split()) for f in files)
        results: list[ImplResult] = []
        for name, tmpl in impls:
            ok = True
            err = None
            t0 = time.perf_counter()
            for f in files:
                if not _run_one(_fill(tmpl, f, out_dir / f"{name}.docx")):
                    ok, err = False, f"conversion failed on {f.name}"
                    break
            elapsed = time.perf_counter() - t0
            results.append(ImplResult(name=name, ok=ok, total_seconds=elapsed, error=err))
        classes.append(ClassResult(name=sc.name, files=len(files),
                                   total_bytes=total_bytes, total_words=total_words, results=results))

    return BenchOutput(classes=classes, impl_names=[n for n, _ in impls],
                       gen_seconds=gen_seconds, output_dir=out_dir, words_per_page=cfg.words_per_page)
