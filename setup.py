from __future__ import annotations

from setuptools import setup
from setuptools.command.build_py import build_py


class _build_py(build_py):
    def run(self) -> None:
        super().run()
        if not self.dry_run:
            self.copy_file("click_llm.pth", self.build_lib)


setup(
    cmdclass={"build_py": _build_py},
)
