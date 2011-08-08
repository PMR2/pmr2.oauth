from zope.annotation import factory as za_factory

def factory(cls, key=None):
    """\
    This specialized annotation factory returns a factory that accepts
    the request attribute such that different layers can be applied to
    acquire the intended `ConsumerManager`.
    """

    original = za_factory(cls, key)

    def getAnnotation(context, request):
        """\
        Call the original factory with just the context.
        """
        return original(context)

    return getAnnotation
