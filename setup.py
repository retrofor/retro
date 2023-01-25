import setuptools

with open("README.md", "rb") as fh:
    long_description = fh.read().decode("utf-8")

setuptools.setup(
    name='retrofor_wut',
    version='3.0.5',
    url='https://github.com/retrofor/retrofor_wut',
    license='GPLV3',
    author='简律纯',
    author_email='HsiangNianian@outlook.com',
    description='Python codes to Flowcharts.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "LICENSE :: OSI APPROVED :: GNU GENERAL PUBLIC LICENSE V3 (GPLV3)",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
    ],
    python_requires='>=3.8',
    install_requires=['astunparse', 'chardet'],
)
