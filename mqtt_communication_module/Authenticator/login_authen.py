from database.user_management.db import authenticate_user

class Authenticator:
    def __init__(self):
        pass

    def authenticate(username, password, use_encryption):
        # user_management authentication through the database
        return authenticate_user(username, password, use_encryption)

