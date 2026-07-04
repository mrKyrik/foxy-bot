import sqlite3

def test():
    user_conn = sqlite3.connect('Data/USER-DB.db')
    cursor = user_conn.cursor()
    try:
        cursor.execute("SELECT e.timestamp, strftime('%s', e.timestamp) FROM db_event_logs e LIMIT 1")
        print("USER-DB Timestamp:", cursor.fetchone())
    except Exception as e:
        print("USER-DB Query: FAILED", e)

if __name__ == '__main__':
    test()
