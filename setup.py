from distutils.core import setup

setup(
    name='WeechatPage',
    version='1.0.0',
    author='Ian Kronquist',
    author_email='iankronquist@gmail.com',
    packages=['weechatpage', 'weechatpage.test'],
    scripts=['bin/stowe-towels.py','bin/wash-towels.py'],
    url='http://pypi.python.org/pypi/WeechatPage/',
    license='LICENSE.txt',
    description='Report WeeChat statuses as desktop notifications',
    long_description=open('README.md').read(),
    install_requires=[
        'Twisted==13.0.0',
        'Parsley==1.1',
        'nose==1.3.0'
    ],
)
