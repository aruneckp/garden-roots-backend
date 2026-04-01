# Follow driver installation and setup instructions here: 
# https://www.oracle.com/database/technologies/appdev/python/quickstartpython.html

import oracledb

DB_USER = "admin"
DB_PASSWORD = "311083@Venki"
WALLET_DIR = "/Users/standard/Downloads/Wallet_gardenroots2026"
WALLET_PASSWORD = "311083"
TNS_NAME = "gardenroots2026_tp"

def run_app():
    try:
        pool = oracledb.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=TNS_NAME,
            config_dir=WALLET_DIR,
            wallet_location=WALLET_DIR,
            wallet_password=WALLET_PASSWORD,
        )
        with pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM DUAL")
                result = cursor.fetchone()
                if result:
                    print(f"Connected successfully! Query result: {result[0]}")
    except oracledb.Error as e:
        print(f"Could not connect to the database - Error occurred: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_app()