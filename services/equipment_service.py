from database import get_connection


def get_all_equipment():

    connection = get_connection()

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM equipment
        ORDER BY equipment_id
    """)

    equipment = cursor.fetchall()

    cursor.close()
    connection.close()

    return equipment