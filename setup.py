from setuptools import setup, find_packages

setup(
    name="quanta_os",
    version="0.2.0",
    description="Quantum operating system prototype with circuit compiler, resource scheduler, and ZMQ protocol layer.",
    author="quanta-os contributors",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.9",
    install_requires=["numpy>=1.24"],
    extras_require={"dev": ["pytest>=7.0"]},
)

#
# ─────────────────────────────────────────────────────────────
# Quanta OS — 版权与出处  |  Copyright & Provenance
# 作者    Author   : DKword17 <19832535010@163.com>
# 版权    Copyright: (c) 2026 DKword17
# 许可证  License  : Apache 2.0（见 LICENSE）
# 仓库    Repo     : https://github.com/DKword17/quanta-os
# Quanta OS 由 DKword17 一人原创并维护，转载/复用请保留本标记。
# ─────────────────────────────────────────────────────────────
