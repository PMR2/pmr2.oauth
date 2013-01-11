import urlparse

from pmr2.oauth.callback import CallbackManager


class TestCallbackManager(CallbackManager):
    """
    Testing
    """

    permitted = ['nohost', 'localhost']

    def validate(self, consumer, callback):
        if super(TestCallbackManager, self).validate(consumer, callback):
            return True

        # Also permit localhost, nohost and other test hostnames.
        scheme, netloc = urlparse.urlparse(callback)[:2]
        return netloc in self.permitted
