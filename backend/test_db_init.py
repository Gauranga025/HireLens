from app.db.database import init_database, engine, AsyncSessionLocal
import traceback

try:
    init_database()
    print('Init succeeded')
    print(f'Engine after init: {engine}')
    print(f'AsyncSessionLocal after init: {AsyncSessionLocal}')
except Exception as e:
    print(f'Init failed: {e}')
    traceback.print_exc()
