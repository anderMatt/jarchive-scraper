#!/usr/bin/env python3
import pymongo

COLLECTION_NAME = "categories"


class DatabaseConnectionError(Exception):
     """Raise when DB is unable to connect to database resource."""
     pass


class Database:
    def __init__(self, host="localhost", port=27017, dbname="jeopardy", collection_name="categories"):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.collection_name = collection_name

    def init_connection(self):
        self.client = pymongo.MongoClient(host=self.host, port=self.port, serverSelectionTimeoutMS=5)
        try:
            self.client.server_info()  # Check conn was successful. Polls for <serverSelectionTimeoutMS passed to client constructor, default=30s>
        except pymongo.errors.ServerSelectionTimeoutError as e:
            raise DatabaseConnectionError("Timed out trying to connect to Mongo server at {}:{}. Please ensure an instance of mongod is running".format(self.host, self.port)) from e


    def save(self, categories_dict):
        for category, clues in categories_dict.items():
            self.client[self.dbname][self.collection_name].insert({  # TODO: chaining access too messy?
                    "category": category,
                    "clues": clues
                })
        return

if __name__ == "__main__":
    pass
