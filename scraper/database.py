#!/usr/bin/env python3
import os
import pymongo
import sqlite3

class DatabaseConnectionError(Exception):
     """Raise when DB is unable to connect to database resource."""
     pass


class Database:

    @classmethod
    def factory(cls, connection_param):
        database_cls = cls.determine_engine(connection_param)
        if not database_cls:
            raise ValueError("Invalid database factory arg!: {}".format(connection_param))
        return database_cls(connection_param)

    @classmethod
    def determine_engine(cls, connection_param):
        if connection_param.startswith("mongodb://"):
            return MongoDatabase
        elif connection_param.startswith("sqlite:///") or connection_param.endswith(".db"):
            return SqliteDatabase
        else:
            return None 




class MongoDatabase:
    def __init__(self, host_uri):
        self.host_uri = host_uri
        self.collection_name = "categories"
        self.client = None
        self.db = None

    def init_connection(self):
        self.client = pymongo.MongoClient(self.host_uri)
        try:
            self.client.server_info()  # Check conn was successful. Polls for <serverSelectionTimeoutMS passed to client constructor, default=30s>
        except pymongo.errors.ServerSelectionTimeoutError as e:
            raise DatabaseConnectionError("Timed out trying to connect to Mongo server at . Please ensure an instance of mongod is running".format(self.host_uri)) from e
        self.db = self.client.get_default_database()  # Database specified in host_uri.


    def save(self, categories_dict):
        for category, clues in categories_dict.items():
            self.db[self.collection_name].insert({  # TODO: chaining access too messy?
                    "category": category,
                    "clues": clues
                })
        return


class SqliteDatabase:

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def init_connection(self):
        if not self._file_exists(self.db_path):
            print("Creating new file: {}".format(self.db_path))
            open(self.db_path, 'w').close() # Create file.
        #try/except
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # self.cursor = self.conn.cursor()
        self._build_tables()

    def save(self, categories_dict):
        cursor = self.conn.cursor()
        for category, clues in categories_dict.items():
            cursor.execute("""INSERT INTO categories(title) VALUES (?)""", (category,))
            category_id = cursor.lastrowid
            for clue in clues:
                cursor.execute("""INSERT INTO clues(question, answer, category) VALUES(?,?,?)""", (clue["question"], clue["answer"], category_id))

            self.conn.commit()
            print('DONE SAVING A CATEGORY!')


    def _file_exists(self, fpath):
        return os.path.isfile(fpath)

    def _build_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS categories(id INT PRIMARY KEY, title TEXT NOT NULL)""")

        cursor.execute("""CREATE TABLE IF NOT EXISTS clues(id INT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category INT NOT NULL,
                    FOREIGN KEY(category) REFERENCES categories(id)
                )""")
        return


if __name__ == "__main__":
    pass
