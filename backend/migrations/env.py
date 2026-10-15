from alembic import context
from sqlalchemy import create_engine
from app.db import Base
from app.core import settings
config=context.config
if context.is_offline_mode():
    context.configure(url=settings.database_url,target_metadata=Base.metadata,literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine=create_engine(settings.database_url)
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
