import ast
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AuditResult:
    """Deterministic System 2 verification outcome (G_det in {0, 1})."""
    passed: bool
    g_det: int
    stage_failed: str | None
    error_traceback: str
    execution_latency_sec: float
    stdout_preview: str


class _SecurityASTVisitor(ast.NodeVisitor):
    """Static AST analyzer enforcing module allowlists and blocking destructive OS/eval calls."""

    ALLOWED_MODULES = {
        "json", "os", "sys", "math", "time", "re", "datetime", "pathlib",
        "typing", "dataclasses", "requests", "urllib", "hashlib", "csv",
        "collections", "itertools", "statistics", "random", "string"
    }

    BANNED_CALLS = {
        "eval", "exec", "compile", "__import__", "system", "popen",
        "remove", "unlink", "rmdir", "removedirs", "rmtree"
    }

    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root_pkg = alias.name.split(".")[0]
            if root_pkg not in self.ALLOWED_MODULES:
                self.violations.append(f"Disallowed import: '{alias.name}' at line {node.lineno}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            root_pkg = node.module.split(".")[0]
            if root_pkg not in self.ALLOWED_MODULES:
                self.violations.append(f"Disallowed from-import: '{node.module}' at line {node.lineno}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in self.BANNED_CALLS:
            self.violations.append(f"Banned function call '{func_name}()' at line {node.lineno}")
        self.generic_visit(node)


class DeterministicAuditor:
    """
    System 2 Verification Gate.
    Validates syntax, enforces static security rules, and runs candidate scripts
    in an isolated child process with strict timeout bounds.
    """

    def __init__(self, sandbox_dir: str | None = None, timeout_sec: int = 30) -> None:
        base_dir = Path(__file__).resolve().parent
        self.sandbox_dir = Path(sandbox_dir) if sandbox_dir else (base_dir / "sandbox")
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_sec = timeout_sec

    def audit_code_and_run(self, script_path: str) -> AuditResult:
        """Executes full 3-stage audit: AST Syntax -> Security Policy -> Subprocess Sandbox."""
        target = Path(script_path).resolve()
        if not target.exists():
            return AuditResult(
                passed=False,
                g_det=0,
                stage_failed="FILE_MISSING",
                error_traceback=f"Target script not found: {target}",
                execution_latency_sec=0.0,
                stdout_preview="",
            )

        source_code = target.read_text(encoding="utf-8")

        # STAGE 1: AST Syntax Verification
        try:
            tree = ast.parse(source_code, filename=str(target))
        except SyntaxError as err:
            return AuditResult(
                passed=False,
                g_det=0,
                stage_failed="AST_SYNTAX",
                error_traceback=f"SyntaxError at line {err.lineno}: {err.msg}",
                execution_latency_sec=0.0,
                stdout_preview="",
            )

        # STAGE 2: Static Security & Allowlist Enforcement
        visitor = _SecurityASTVisitor()
        visitor.visit(tree)
        if visitor.violations:
            return AuditResult(
                passed=False,
                g_det=0,
                stage_failed="SECURITY_POLICY",
                error_traceback="; ".join(visitor.violations),
                execution_latency_sec=0.0,
                stdout_preview="",
            )

        # STAGE 3: Isolated Subprocess Sandbox Execution
        start_time = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(target)],
                cwd=str(self.sandbox_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
            )
            elapsed = round(time.perf_counter() - start_time, 3)

            if proc.returncode != 0:
                stderr_clean = (proc.stderr or proc.stdout).strip()[-1200:]
                return AuditResult(
                    passed=False,
                    g_det=0,
                    stage_failed="RUNTIME_EXIT_NONZERO",
                    error_traceback=f"Exit code {proc.returncode}:\n{stderr_clean}",
                    execution_latency_sec=elapsed,
                    stdout_preview=proc.stdout.strip()[:400],
                )

            return AuditResult(
                passed=True,
                g_det=1,
                stage_failed=None,
                error_traceback="",
                execution_latency_sec=elapsed,
                stdout_preview=proc.stdout.strip()[:400],
            )

        except subprocess.TimeoutExpired:
            elapsed = round(time.perf_counter() - start_time, 3)
            return AuditResult(
                passed=False,
                g_det=0,
                stage_failed="TIMEOUT_EXCEEDED",
                error_traceback=f"Execution exceeded sandbox ceiling of {self.timeout_sec}s.",
                execution_latency_sec=elapsed,
                stdout_preview="",
            )
        except Exception as err:
            elapsed = round(time.perf_counter() - start_time, 3)
            return AuditResult(
                passed=False,
                g_det=0,
                stage_failed="SANDBOX_EXCEPTION",
                error_traceback=str(err),
                execution_latency_sec=elapsed,
                stdout_preview="",
            )