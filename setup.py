from setuptools import setup
import notify_ios
import os

setup(
    author='Stephen Muss',
    author_email='stephenmuss@gmail.com',
    name='django-notify-ios',
    version=notify_ios.VERSION,
    description='Django Notify iOS makes it easy to send push notifications to iOS devices',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
    url='https://github.com/stephenmuss/django-notify-ios',
    license='BSD License',
    packages=['notify_ios'],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
    zip_safe=False
)
