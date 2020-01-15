import io
from distutils.command.build import build
from itertools import chain
from os.path import basename, dirname, join

from setuptools import Command, find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.easy_install import easy_install
from setuptools.command.install_lib import install_lib


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8"),
    ).read()


class BuildWithPTH(build):
    def run(self, *args, **kwargs):
        build.run(self)
        path = join(dirname(__file__), "static", "brm.pth")
        dest = join(self.build_lib, basename(path))
        self.copy_file(path, dest)


class EasyInstallWithPTH(easy_install):
    def run(self, *args, **kwargs):
        easy_install.run(self)
        path = join(dirname(__file__), "static", "brm.pth")
        dest = join(self.install_dir, basename(path))
        self.copy_file(path, dest)


class InstallLibWithPTH(install_lib):
    def run(self, *args, **kwargs):
        install_lib.run(self)
        path = join(dirname(__file__), "static", "brm.pth")
        dest = join(self.install_dir, basename(path))
        self.copy_file(path, dest)
        self.outputs = [dest]

    def get_outputs(self):
        return chain(install_lib.get_outputs(self), self.outputs)


class DevelopWithPTH(develop):
    def run(self, *args, **kwargs):
        develop.run(self)
        path = join(dirname(__file__), "static", "brm.pth")
        dest = join(self.install_dir, basename(path))
        self.copy_file(path, dest)


class GeneratePTH(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self, *args, **kwargs):
        with open(join(dirname(__file__), "static", "brm.pth"), "w") as fh:
            with open(join(dirname(__file__), "static", "brm.embed")) as sh:
                fh.write(
                    "import sys;" "exec(%r)" % sh.read().replace("    ", " ")
                )


setup(
    cmdclass={
        "build": BuildWithPTH,
        "easy_install": EasyInstallWithPTH,
        "install_lib": InstallLibWithPTH,
        "develop": DevelopWithPTH,
        "genpth": GeneratePTH,
    },
)
