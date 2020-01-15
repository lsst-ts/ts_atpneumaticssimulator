
from setuptools import setup, find_namespace_packages

install_requires = []
tests_requires = ["pytest", "pytest-flake8"]
dev_requires = install_requires + tests_requires + ["documenteer[pipelines]"]
scm_version_template = """# Generated by setuptools_scm
__all__ = ["__version__"]

__version__ = "{version}"
"""

setup(
    name="ts_ATPneumaticsSimulator",
    description="Installs python code for ts_ATPneumaticsSimulator.",
    use_scm_version={"write_to": "python/lsst/ts/ATPneumaticsSimulator/version.py",
                     "write_to_template": scm_version_template},
    setup_requires=["setuptools_scm"],
    package_dir={"": "python"},
    packages=find_namespace_packages(where="python"),
    scripts=["bin/run_atpneumatics_simulator.py"],
    tests_require=tests_requires,
    extras_require={"dev": dev_requires},
    license="GPL"
)
