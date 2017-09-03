import setuptools

setuptools.setup(
    name="matrix_appservice_hangouts",
    version="0.1.0",
    url="https://github.com/cadair/matrix-appservice-hangouts",

    author="Stuart Mumford",
    author_email=" ",

    description="A Python 3.6 matrix <> hangouts appservice.",
    long_description=open('README.rst').read(),

    packages=setuptools.find_packages(),

    install_requires=['aiohttp',
                      ''],

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    entry_points='''
        [console_scripts]
        hangoutsas=matrix_appservice_hangouts.__main__:main
    ''',
)
