import os
from io import open
from pathlib import Path

from setuptools import setup, find_packages

with open(os.path.join(Path(__file__).parent / 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Se leen los requirements de requirements.txt
with open(os.path.join(Path(__file__).parent, 'requirements.txt'), encoding='utf-8') as f:
    requirements = f.read().splitlines()
#

main_folder = Path(__file__).parents[4]
os.chdir(main_folder)

with open(main_folder / "VERSION", "r") as reader:
    VERSION = reader.read().strip()

setup(
    name='streamlit-component-label-studio',
    version=VERSION,
    license='MIT',
    url='https://github.com/quiradev/streamlit-plugins',
    description='Label Studio Component of streamlit, its a port of the Label Studio platform into streamlit',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author_email='v.quilonr@gmail.com',
    author='Victor Quilon Ranera',
    packages=find_packages(include=["streamlit_plugins.components.label_studio", "streamlit_plugins.components.label_studio.*"]),
    python_requires='>=3.9',
    install_requires=requirements,
    include_package_data=True,
    package_data={
          "streamlit_plugins.components.label_studio": ["frontend/build/**/*"]
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    keywords=["streamlit", "plugins", "components", "label studio"],
    options={
        'sdist': {'dist_dir': './dist/streamlit-plugins-component-label-studio'},
        'bdist_wheel': {'dist_dir': './dist/streamlit-plugins-component-label-studio'},
        'build': {'build_base': './build/streamlit-plugins-component-label-studio'}
    }
)
