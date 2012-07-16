from setuptools import setup, find_packages
import ios_notifications
import os

setup(
    author='Stephen Muss',
    author_email='stephenmuss@gmail.com',
    name='django-ios-notifications',
    version=ios_notifications.VERSION,
    description='Django iOS Notifications makes it easy to send push notifications to iOS devices',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
    url='https://github.com/stephenmuss/django-ios-notifications',
    download_url='https://github.com/stephenmuss/django-ios-notifications/zipball/v0.1.2',
    license='BSD License',
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
    install_requires=[
        'Django>=1.3',
        'pyOpenSSL>=0.10',
        'django-fields>=0.1.2'
    ],
    zip_safe=False
)
