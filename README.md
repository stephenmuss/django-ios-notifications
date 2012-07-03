django-ios-notifications
=================

Django iOS Notifications makes it easy to send push notifications to iOS devices.


Installation
-----------------

You can install with pip: `pip install git+git://github.com/stephenmuss/django-ios-notifications.git`.

You then need to add `ios_notifications` to `INSTALLED_APPS` in your settings file.

If you want to use the API for registering devices you will also need to make the appropriate changes to your urls file:

    urlpatterns = patterns('',
        ...
        url(r'^ios-notifications/', include('ios_notifications.urls')),
        ...
    )

After that you will need to run `./manage.py syncdb` to create the database tables required for django-ios-notifications.


Setting up the APN Services
-----------------

Before you can add some devices and push notifications you'll need to set up an APN Service.
An example of how to do this in a development environment follows.

Start up your development server: `./manage.py runserver` and open up the following url in a web browser http://127.0.0.1:8000/admin/ios_notifications/apnservice/add/. You'll see a form to be able to create a new APN Service.

I am making the assumption that you have already created a private key and certificate. If not I suggest you follow one of the online guides to complete this step. One such example can be found at http://www.raywenderlich.com/3443/apple-push-notification-services-tutorial-part-12

The name of the service can be any arbitrary string.

The hostname will need to be a valid hostname for one of the Apple APN Service hosts. Currently this is `gateway.sandbox.push.apple.com` for sandbox testing and `gateway.push.apple.com` for production use.

For the certificate and private key fields paste in your certificate and key including the lines with `----BEGIN CERTIFICATE-----`, `-----END CERTIFICATE-----`, `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`.

After this you are ready to save the APN Service.


Registering devices
-----------------

There are a few different ways you can register a device. You can either create the device in the admin interface at http://127.0.0.1:8000/admin/ios_notifications/device/add/ or use the API provided by django-ios-notifications to do so.

If you want to add the device through the admin interface you will need to know the device's token represented by 64 hexadecimal characters (be sure to exclude any `<`, `>` and whitespace characters).

Otherwise the django-ios-notifications API provides a REST interface for you to be able to add the device; this would normally be done by sending a request from you iOS app.

To register your device you will need to make a POST request from your device and pass the appropriate parameters as part of the URL.

The URL requires you to substitute in the device's 64 character hexadecimal token and the id of the APN Service to associate with this device.

For example if you wanted to register a device with the token `0fd12510cfe6b0a4a89dc7369d96df956f991e66131dab63398734e8000d0029` using an APN Service with the id 10 you would make a POST request to the following location:
http://127.0.0.1:8000/ios-notifications/register-device/0fd12510cfe6b0a4a89dc7369d96df956f991e66131dab63398734e8000d0029/10/

You do not need to pass any parameters as part of the request body.

The API will return you a response in JSON format to let you know whether your request was successful or not.




NOTE: This is a work in progress and is far from being production ready.
Use at your own risk.
