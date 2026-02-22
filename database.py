import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # change if needed
        password="Jana@2004",  # put your MySQL password
        database="smart_healthcare"
    )
