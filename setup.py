from setuptools import setup, find_packages

requires = [
    'Redis',
    'Distribute',
    'Mako',
]
entry_points = """
"""

try:
    with open('README.txt') as file:
        long_desc = file.read()
except:
    long_desc = "TBD"

setup(name="BIPostal",
      author="Mozilla Services Group",
      description="Postfix/Sendmail Milter for BrowserId address tokens",
      long_description=long_desc,
      author_email="dev_services@mozilla.com",
      version=0.5,
      packages=find_packages(),
      entry_points=entry_points,
      install_requires=requires,
      license='MPL')
