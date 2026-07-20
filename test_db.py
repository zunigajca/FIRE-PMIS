from database import get_connection

connection = get_connection()

print("Connected!")

connection.close()