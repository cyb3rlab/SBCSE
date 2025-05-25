import bcrypt
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine, Column, Integer, String, Boolean

# SQLite db engine
db_path = 'database/user_management/users.db'
engine = create_engine(f'sqlite:///{db_path}', echo=True)
#engine = create_engine(f'sqlite:///{db_path}', echo=False)
Base = declarative_base()


# Encrypted
class EncryptedUser(Base):
    __tablename__ = 'encrypted_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    is_authorized = Column(Boolean, default=False)  # 授权

# Explicit part
class PlainUser(Base):
    __tablename__ = 'plain_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)

# Creating a database Session
Session = sessionmaker(bind=engine)
session = Session()


def init_db(use_encryption):
    print("Initializing database...")
    Base.metadata.create_all(engine)

    # Managing Sessions with scoped_session
    session = Session()

    # Check and create encrypted users
    for username, password in [("RPF", "123"), ("BOS", "456")]:
        if not session.query(EncryptedUser).filter_by(username=username).first():
            salt = bcrypt.gensalt().decode('utf-8')
            user = EncryptedUser(
                username=username,
                password=hash_password_with_salt(password, salt),
                salt=salt,
                is_authorized=True
            )
            session.add(user)

    # Check and create plaintext users
    for username, password in [("RPF", "123"), ("BOS", "456")]:
        if not session.query(PlainUser).filter_by(username=username).first():
            user = PlainUser(username=username, password=password)
            session.add(user)

    session.commit()

def user_login(username, password):
    session = Session()  # Using Sessions
    try:
        # Getting Authorized Salt
        salt = get_authorized_salt(username)
        # print(f"Retrieved salt for {username}: {salt}")
        if salt:
            hashed_password = hash_password_with_salt(password, salt)
            user = session.query(EncryptedUser).filter_by(username=username).first()
            if user:

                if hashed_password == user.password:
                    print(f"{username} Login successful!++++++++++++++++++++++++++++++++")
                    return True
                else:
                    print("Login failed. Incorrect password.")
            else:
                print("Login failed. user_management not found.")
        else:
            print("Login failed. user_management not authorized.")
            return False

    finally:
        session.close()  # Ensure that the session is closed


# User_Authentication
def authenticate_user(username, password, use_encryption):
    if use_encryption:
        if user_login(username,password):
            return True
    else:
        user = session.query(PlainUser).filter_by(username=username).first()
        if user and user.password == password:
            print(f"Authenticated: {user.username}")
            return True

    print("Authentication failed.")
    return False

def get_authorized_salt(username):
    user = session.query(EncryptedUser).filter_by(username=username).first()
    if user and user.is_authorized:
        return user.salt
    return None

# Compare plaintext passwords
# Obtain user credentials (authorize users to obtain salt and hash passwords using plaintext passwords)
def get_authorized_credentials(username, use_encryption):
    if use_encryption:
        user = session.query(EncryptedUser).filter_by(username=username).first()
        if user and user.is_authorized:
            return user.password, user.salt
    else:
        user = session.query(PlainUser).filter_by(username=username).first()
        if user:
            return user.password, None  # Salt values are not required for plaintext users
    return None, None

def print_users():
    encrypted_users = session.query(EncryptedUser).all()
    plain_users = session.query(PlainUser).all()

    print("Encrypted Users:")
    for user in encrypted_users:
        print(f"Username: {user.username}, Password Hash: {user.password}, Salt: {user.salt}, Authorized: {user.is_authorized}")

    print("Plain Users:")
    for user in plain_users:
        print(f"Username: {user.username}, Password: {user.password}")

# hash password
def hash_password_with_salt(password, salt):
    return bcrypt.hashpw(password.encode('utf-8'), salt.encode('utf-8')).decode('utf-8')
