from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in bwmp_erpnext/__init__.py
from bwmp_erpnext import __version__ as version

setup(
	name="bwmp_erpnext",
	version=version,
	description="Banaraswala Wire Mesh Private Limited",
	author="Frappe",
	author_email="test@test.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
