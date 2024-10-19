import keyring


def get_required_password(service_name: str, username: str) -> str:  # pragma: no cover
    """
    Retrieve a password from the keychain, or throw if it's missing.
    """
    # We wrap this API because keyring will return ``None`` rather
    # than tell you a password is missing, e.g.
    #
    #     >>> import keyring
    #     >>> pw = keyring.get_password("doesnotexist", "doesnotexist")
    #     >>> print(pw)
    #     None
    #
    # It's better to throw an error early than let this empty value
    # propagate into our code and bubble up elsewhere.
    #
    # e.g. if we're calling the Flickr API using an API key retrieved
    # using keyring, we'd rather know immediately that it's empty than
    # get a cryptic "invalid API key" error from the Flickr API.
    #
    password = keyring.get_password(service_name, username)

    if password is None:
        raise RuntimeError(f"Could not retrieve password {(service_name, username)}")

    return password
