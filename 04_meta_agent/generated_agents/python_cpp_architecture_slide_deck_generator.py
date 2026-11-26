import os
import sys
import json
import pathlib
from typing import Dict, Any, List


def create_markdown_cell(content: str, slide_type: str = "slide") -> Dict[str, Any]:
    """Construct an nbformat v4 markdown cell configured for RISE/nbconvert slideshows."""
    return {
        "cell_type": "markdown",
        "metadata": {
            "slideshow": {
                "slide_type": slide_type
            }
        },
        "source": [line + "\n" for line in content.split("\n")]
    }


def create_code_cell(code: str, slide_type: str = "fragment", outputs: List[Any] = None) -> Dict[str, Any]:
    """Construct an nbformat v4 code cell with optional slide metadata."""
    if outputs is None:
        outputs = []
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {
            "slideshow": {
                "slide_type": slide_type
            }
        },
        "outputs": outputs,
        "source": [line + "\n" for line in code.split("\n")]
    }


def build_notebook_deck() -> Dict[str, Any]:
    """Assemble a comprehensive, green-themed slide deck comparing Python and C++ architecture."""
    css_theme = """<style>
.green-card {
    background: linear-gradient(135deg, #0b3d20 0%, #17542d 100%);
    color: #f1f8e9;
    padding: 24px;
    border-radius: 12px;
    border-left: 8px solid #00e676;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
    margin-bottom: 20px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}
.green-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin: 15px 0;
}
.green-box-py {
    background: #e8f5e9;
    border: 2px solid #43a047;
    border-radius: 8px;
    padding: 16px;
    color: #1b5e20;
}
.green-box-cpp {
    background: #f1f8e9;
    border: 2px solid #2e7d32;
    border-radius: 8px;
    padding: 16px;
    color: #0d3813;
}
.green-badge {
    background-color: #00e676;
    color: #052c13;
    font-weight: bold;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.85em;
    display: inline-block;
    margin-bottom: 8px;
}
.green-table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
}
.green-table th {
    background-color: #1b5e20;
    color: #ffffff;
    padding: 12px;
    text-align: left;
    border: 1px solid #2e7d32;
}
.green-table td {
    padding: 10px;
    border: 1px solid #c8e6c9;
    background-color: #f9fbf9;
    color: #1b5e20;
}
.green-table tr:nth-child(even) td {
    background-color: #e8f5e9;
}
</style>"""

    cells = []

    # Slide 1: Title Slide
    slide1 = f"""{css_theme}
<div class="green-card">
  <span class="green-badge">ARCHITECTURAL DEEP-DIVE</span>
  <h1 style="color: #a7f3d0; margin-top: 5px; font-size: 2.3em;">Python vs C++ Architecture</h1>
  <h3 style="color: #ecfdf5; font-weight: 300;">Execution Models, Memory Topology, Type Systems & Computational Trade-offs</h3>
  <p style="color: #bbf7d0; font-size: 0.95em; margin-top: 20px;">
    <em>Visualized & Styled under the Green Terminal Architectural Theme</em>
  </p>
</div>"""
    cells.append(create_markdown_cell(slide1, "slide"))

    # Slide 2: Execution Pipelines
    slide2 = """<div class="green-card">
  <h2>1. Execution Pipeline: Compilation vs Interpretation</h2>
  <p>How instructions traverse from human syntax to physical CPU execution.</p>
</div>

<div class="green-grid">
  <div class="green-box-py">
    <h3>Python (CPython)</h3>
    <ul>
      <li><strong>Source code (.py)</strong> parsed into AST.</li>
      <li>AST compiled into portable <strong>Bytecode (.pyc)</strong>.</li>
      <li><strong>CPython VM</strong> interprets opcode loop (<code>ceval.c</code>).</li>
      <li>Abstracted away from registers and micro-architectural pipelining.</li>
      <li>Runtime dispatch tax on every opcode evaluation.</li>
    </ul>
  </div>
  <div class="green-box-cpp">
    <h3>C++ (AOT Compiler)</h3>
    <ul>
      <li><strong>Source code (.cpp)</strong> parsed into AST + Intermediate Representation (IR).</li>
      <li>LLVM/GCC optimizer carries out inlining, vectorization (SIMD), loop unrolling.</li>
      <li>Emits <strong>native machine instructions (ELF / Mach-O / PE)</strong>.</li>
      <li>Direct execution on physical microarchitecture (Registers, ALU, L1/L2 caches).</li>
      <li>Zero runtime interpreter overhead.</li>
    </ul>
  </div>
</div>"""
    cells.append(create_markdown_cell(slide2, "slide"))

    # Slide 3: Memory Models & Layouts
    slide3 = """<div class="green-card">
  <h2>2. Memory Model & Object Layout</h2>
  <p>Contrast between boxed heap references and zero-cost stack abstractions.</p>
</div>

<div class="green-grid">
  <div class="green-box-py">
    <h3>Python: Boxing & Heavyweight <code>PyObject</code></h3>
    <ul>
      <li>Everything is an object dynamically allocated on heap (via <code>PyObject_Malloc</code>).</li>
      <li>Small integer: 28 bytes header (refcount + type pointer + size + ob_digit).</li>
      <li>Arrays are pointers to pointers (cache misses and pointer chasing).</li>
      <li><strong>Memory Management:</strong> Reference Counting + Cyclic Tracing GC.</li>
    </ul>
  </div>
  <div class="green-box-cpp">
    <h3>C++: Primitive Value Semantics & RAII</h3>
    <ul>
      <li>Primitives reside directly in registers or stack frames (<code>int</code> = 4 bytes).</li>
      <li>Aggregates are packed contiguously in cache lines (spatial locality).</li>
      <li><strong>Resource Acquisition Is Initialization (RAII):</strong> Deterministic destruction.</li>
      <li>Optional smart pointers (<code>std::unique_ptr</code>, <code>std::shared_ptr</code>) with explicit zero-overhead contracts.</li>
    </ul>
  </div>
</div>"""
    cells.append(create_markdown_cell(slide3, "slide"))

    # Slide 4: Interactive Introspection Code Cell
    code_introspection = """import sys

# Python Object Overhead Demonstration
small_int = 42
float_val = 3.14159
empty_list = []

print(f"[Python Introspection in Emerald Theme]")
print(f"Size of int (42): {sys.getsizeof(small_int)} bytes  (vs C++ int: 4 bytes)")
print(f"Size of float:    {sys.getsizeof(float_val)} bytes  (vs C++ double: 8 bytes)")
print(f"Size of list():   {sys.getsizeof(empty_list)} bytes (dynamic heap header)")

# Reference count inspection
print(f"Initial Refcount of small_int: {sys.getrefcount(small_int)}")
"""
    cells.append(create_code_cell(code_introspection, "fragment"))

    # Slide 5: Type Systems
    slide5 = """<div class="green-card">
  <h2>3. Type System: Static Nominal vs Dynamic Duck Typing</h2>
  <p>Verification at compile-time vs attribute dispatch at runtime.</p>
</div>

<table class="green-table">
  <thead>
    <tr>
      <th>Dimension</th>
      <th>Python</th>
      <th>C++</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Binding Timing</strong></td>
      <td>Dynamic (types bound to values in heap at runtime)</td>
      <td>Static (types bound to variables/identifiers at compile time)</td>
    </tr>
    <tr>
      <td><strong>Enforcement</strong></td>
      <td>Strong dynamic: cannot implicitly add <code>"4" + 2</code></td>
      <td>Strong static with explicit or implicit promotions / casts</td>
    </tr>
    <tr>
      <td><strong>Polymorphism</strong></td>
      <td>Duck typing (dynamic lookup via <code>tp_getattro</code>)</td>
      <td>Templates (monomorphization) & VTable virtual dispatch</td>
    </tr>
    <tr>
      <td><strong>Cost of Polymorphism</strong></td>
      <td>High hash-map dictionary lookup overhead</td>
      <td>Zero runtime cost (templates) or single memory dereference (VTable)</td>
    </tr>
  </tbody>
</table>"""
    cells.append(create_markdown_cell(slide5, "slide"))

    # Slide 6: Concurrency & Hardware Utilization
    slide6 = """<div class="green-card">
  <h2>4. Concurrency, Parallelism & Microarchitecture</h2>
  <p>Navigating physical multi-core execution bounds.</p>
</div>

<div class="green-grid">
  <div class="green-box-py">
    <h3>CPython: Global Interpreter Lock (GIL)</h3>
    <ul>
      <li>Global lock safeguards refcounts and non-atomic internal state.</li>
      <li>One native OS thread executes Python bytecode at a given moment per process.</li>
      <li>Concurrency via <code>asyncio</code> (cooperative I/O) or <code>multiprocessing</code> (IPC overhead).</li>
      <li>Cache thrashing due to indirect pointer jumping.</li>
    </ul>
  </div>
  <div class="green-box-cpp">
    <h3>C++: Memory Model & Direct Threading</h3>
    <ul>
      <li>Standardized multi-threaded memory model (<code>std::atomic</code>, <code>std::memory_order</code>).</li>
      <li>Unrestricted true SMP parallelism across all CPU cores.</li>
      <li>Direct control over false sharing via <code>alignas(64)</code> cache-line boundary matching.</li>
      <li>Zero GC pauses, predictable real-time deadline guarantees.</li>
    </ul>
  </div>
</div>"""
    cells.append(create_markdown_cell(slide6, "slide"))

    # Slide 7: Architectural Summary & Convergence
    slide7 = """<div class="green-card">
  <h2>5. Architectural Convergence: Modern Hybrid Patterns</h2>
  <p>How contemporary software systems balance developer ergonomics and bare-metal speed.</p>
</div>

<div class="green-box-py" style="margin-top: 15px;">
  <h3 style="color: #1b5e20;">The Symbiotic Architecture (Glue + Engine)</h3>
  <p>Modern high-performance ecosystems (e.g., PyTorch, NumPy, Polars, TensorRT) utilize a hybrid model:</p>
  <ul>
    <li><strong>Python Frontend:</strong> Dynamic DSL, high developer velocity, interactive experimentation, AST instrumentation.</li>
    <li><strong>C++ / CUDA Backend:</strong> Cache-coherent contiguous tensors, SIMD vectorization, multi-threaded work-stealing, deterministic memory reclamation.</li>
    <li><strong>C-API / PyBind11 Bridge:</strong> Zero-copy pointer exchange through buffer protocols (<code>Py_buffer</code>).</li>
  </ul>
</div>"""
    cells.append(create_markdown_cell(slide7, "slide"))

    notebook = {
        "cells": cells,
        "metadata": {
            "celltoolbar": "Slideshow",
            "language_info": {
                "name": "python",
                "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            },
            "slideshow": {
                "theme": "green"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }
    return notebook


def run_agent() -> Dict[str, Any]:
    """Execute artifact generator and save valid .ipynb slide deck."""
    output_filename = "python_vs_cpp_architecture_slides.ipynb"
    target_path = pathlib.Path.cwd() / output_filename
    
    deck = build_notebook_deck()
    
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(deck, f, indent=2)
        
    file_size = target_path.stat().st_size
    total_cells = len(deck["cells"])
    markdown_cells = sum(1 for c in deck["cells"] if c["cell_type"] == "markdown")
    code_cells = sum(1 for c in deck["cells"] if c["cell_type"] == "code")
    
    return {
        "status": "success",
        "artifact_file": str(target_path.name),
        "full_path": str(target_path.resolve()),
        "file_size_bytes": file_size,
        "total_cells": total_cells,
        "markdown_slides": markdown_cells,
        "code_cells": code_cells,
        "theme": "green-visuals",
        "nbformat_version": f"{deck['nbformat']}.{deck['nbformat_minor']}"
    }


if __name__ == '__main__':
    result = run_agent()
    print(json.dumps(result, indent=2))