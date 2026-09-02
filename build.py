"""
build.py — Quanta OS Cython 编译构建脚本

将核心模块编译为 .so 二进制文件，保护源码不被读取和修改。
入口文件保留为 .py 薄层。

用法:
    python build.py          # 编译所有模块
    python build.py clean    # 清理编译产物
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent

# 需要编译为 .so 的模块（相对于项目根目录）
COMPILE_MODULES = [
    "kernel/circuit_compiler",
    "kernel/calibration_protocol",
    "kernel/resource_scheduler",
    "kernel/zmq_protocol",
    "kernel/fourier_adaptive",
    "evolution_engine/self_evolve",
    "evolution_engine/vqc_compiler",
    "evolution_engine/pulse_optimizer",
    "evolution_engine/backends/__init__",
    "simulator/hw_sim_platform",
    "simulator/noise_channel",
    "simulator/experiment_runner",
    "simulator/architectures/__init__",
]

# 保留为 .py 的入口文件
KEEP_PY = [
    "quanta_os.py",
    "quanta_api.py",
    "_provenance.py",
]


def get_python_include():
    """获取 Python 头文件路径"""
    import sysconfig
    return sysconfig.get_config_var("INCLUDEPY") or "/usr/include/python3.14"


def clean():
    """清理编译产物"""
    for mod in COMPILE_MODULES:
        for ext in [".c", ".so", ".html"]:
            for f in ROOT.rglob(f"{Path(mod).name}{ext}"):
                f.unlink()
                print(f"  rm  {f}")
    for d in [ROOT / "build", ROOT / "dist"]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  rm  {d}/")
    print("Clean done.")


def build():
    """使用 Cython 编译模块为 .so"""
    print("=== Quanta OS Cython Build ===")
    print(f"Python: {sys.version}")

    try:
        import Cython
        print(f"Cython: {Cython.__version__}")
    except ImportError:
        print("ERROR: Cython not installed. Run: pip install cython")
        return 1

    include = get_python_include()
    print(f"Include: {include}")
    print()

    ok = 0
    fail = 0
    for mod_path in COMPILE_MODULES:
        py_file = ROOT / f"{mod_path}.py"
        if not py_file.exists():
            print(f"  SKIP {mod_path} (not found)")
            continue

        # 生成 .c 文件
        c_file = ROOT / f"{mod_path}.c"
        cython_bin = ROOT / ".venv-quanta" / "bin" / "cython"
        if not cython_bin.exists():
            cython_bin = "cython"
        result = subprocess.run(
            [str(cython_bin), "-3", str(py_file), "-o", str(c_file)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  FAIL[cyth] {mod_path}")
            for line in (result.stderr or "").strip().split("\n")[:3]:
                print(f"    {line}")
            fail += 1
            continue

        # 编译 .c 到 .so
        mod_name = Path(mod_path).name
        so_file = ROOT / f"{mod_path}.cpython-314-x86_64-linux-gnu.so"
        gcc_cmd = [
                "gcc", "-shared", "-fPIC", "-O2", "-fvisibility=hidden",
                f"-I{include}",
                "-o", str(so_file),
                str(c_file),
                "-lpython3.14",
            ]
        result = subprocess.run(gcc_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FAIL[gcc] {mod_path}")
            for line in (result.stderr or "").strip().split("\n")[:3]:
                print(f"    {line}")
            fail += 1
            continue

        # 清理 .c 文件
        c_file.unlink()
        ok += 1
        print(f"  OK   {mod_path} -> .so")

    print()
    print(f"Build complete: {ok} OK, {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean()
    else:
        build()


if __name__ == "__main__":
    sys.exit(main())