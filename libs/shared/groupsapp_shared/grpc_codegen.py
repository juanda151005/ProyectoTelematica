"""Generate gRPC Python stubs from proto/ at import time.

Running ``python -m groupsapp_shared.grpc_codegen`` compiles the .proto
files into ``groupsapp_shared.proto_gen``. Each service runs this in its
Dockerfile so we never commit generated code.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys


def _find_proto_dir() -> pathlib.Path:
    override = os.getenv("PROTO_DIR")
    if override and pathlib.Path(override).exists():
        return pathlib.Path(override)
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "proto"
        if candidate.is_dir() and any(candidate.glob("*.proto")):
            return candidate
    raise FileNotFoundError("proto/ directory not found")


def generate(out_dir: pathlib.Path | None = None) -> None:
    proto_dir = _find_proto_dir()
    out = out_dir or (pathlib.Path(__file__).resolve().parent / "proto_gen")
    out.mkdir(parents=True, exist_ok=True)
    (out / "__init__.py").touch()

    files = sorted(proto_dir.glob("*.proto"))
    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"-I{proto_dir}",
        f"--python_out={out}",
        f"--grpc_python_out={out}",
        *[str(f) for f in files],
    ]
    subprocess.check_call(cmd)

    # Fix relative imports in generated *_pb2_grpc.py files
    for grpc_py in out.glob("*_pb2_grpc.py"):
        text = grpc_py.read_text()
        for pb in out.glob("*_pb2.py"):
            mod = pb.stem
            text = text.replace(f"import {mod} as", f"from . import {mod} as")
        grpc_py.write_text(text)

    print(f"Generated stubs in {out}")


if __name__ == "__main__":
    generate()
