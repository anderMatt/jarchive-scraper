#!/usr/bin/env python3
import os
import pymongo
import sqlite3
from .database_status_codes import DATABASE_STATUS_CODES

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
        self.db_status = DATABASE_STATUS_CODES["not connected"]

    def init_connection(self):
        print("Attempting to connect to {}".format(self.host_uri))
        self.client = pymongo.MongoClient(self.host_uri)

        try:
            self.client.server_info()  # Check conn was successful. Polls for <serverSelectionTimeoutMS passed to client constructor, default=30s>
        except pymongo.errors.ServerSelectionTimeoutError as e:
            self.db_status = DATABASE_STATUS_CODES["failure"]
            raise DatabaseConnectionError("Timed out trying to connect to Mongo server at . Please ensure an instance of mongod is running".format(self.host_uri)) from e

        self.db_status = DATABASE_STATUS_CODES["success"]
        self.db = self.client.get_default_database()  # Database specified in host_uri.
        print("Connection successful. Category collections will be saved to {}".format(self.db.name))


    def save(self, categories_dict):
        for category, clues in categories_dict.items():
            self.db[self.collection_name].insert({  # TODO: chaining access too messy?
                    "category": category,
                    "clues": clues
                })
        return

    def get_connection_status(self):
        return self.db_status


class SqliteDatabase:

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.db_status = DATABASE_STATUS_CODES["not connected"]

        #TODO: define sql strings here.

    def init_connection(self):
        print("Attempting to connect to {}".format(self.db_path))
        if not self._file_exists(self.db_path):
            print("Creating new file: {}".format(self.db_path))
            open(self.db_path, 'w').close() # Create file.

        try:
            self.conn = sqlite3.connect(self.db_path)
            self._build_tables()
            self.db_status = DATABASE_STATUS_CODES["success"]
        except Exception as e:
            self.db_status = DATABASE_STATUS_CODES["failure"]

    def save(self, categories_dict):
        cursor = self.conn.cursor()
        for category, clues in categories_dict.items():
            cursor.execute("""INSERT INTO categories(title) VALUES (?)""", (category,))
            category_id = cursor.lastrowid
            for clue in clues:
                cursor.execute("""INSERT INTO clues(question, answer, category_id) VALUES(?,?,?)""", (clue["question"], clue["answer"], category_id))

            self.conn.commit()
        return


    def _file_exists(self, fpath):
        return os.path.isfile(fpath)

    def _build_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY, title TEXT NOT NULL)""")

        cursor.execute("""CREATE TABLE IF NOT EXISTS clues(id INTEGER PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category_id INT NOT NULL,
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                )""")
        self.conn.commit()
        cursor.close()

    def get_connection_status(self):
        return self.db_status



if __name__ == "__main__":
    pass
