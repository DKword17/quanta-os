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
