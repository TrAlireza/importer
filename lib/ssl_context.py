import ssl


def relaxed_context():
    """
    unsafe as checking hostname and certificate verification are disabled.
    """
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context
