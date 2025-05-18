import psycopg2

class ConnectDB:
    def __init__(self, host, user, password, database, port):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None

    def connect(self):
        self.connection = psycopg2.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            dbname=self.database,
            port=self.port
        )
        print("Database connection established.")
        return self.connection

    def close(self):
        if self.connection:
            self.connection.close()
            print("Database connection closed.")