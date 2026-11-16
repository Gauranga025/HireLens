import app.db.database as db_module
import traceback

print(f'Before init - engine: {db_module.engine}')
print(f'Before init - AsyncSessionLocal: {db_module.AsyncSessionLocal}')

try:
    db_module.init_database()
    print('Init succeeded')
    print(f'After init - engine: {db_module.engine}')
    print(f'After init - AsyncSessionLocal: {db_module.AsyncSessionLocal}')
except Exception as e:
    print(f'Init failed: {e}')
    traceback.print_exc()
