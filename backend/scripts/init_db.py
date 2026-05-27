from app.shared.base_model import Base
from app.core.database import engine

# Create all tables synchronously using the engine's sync interface
Base.metadata.create_all(bind=engine.sync_engine)
print('Created all tables (sync)')
