import asyncio
import json
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from app.db.session import engine, AsyncSessionLocal
from app.db.models import Base, User, Template
from app.security.auth import get_password_hash
from app.core.config import settings

logger = logging.getLogger(__name__)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
async def seed_admin(db: AsyncSession):
    email = settings.admin_email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=email,
            password_hash=get_password_hash(settings.admin_password),
            role="admin"
        )
        db.add(user)
        try:
            await db.commit()
            print(f"Created admin user: {email}")
        except IntegrityError:
            await db.rollback()
            print("Admin user already exists.")
    else:
        print(f"Admin user already exists: {email}")

async def seed_templates(db: AsyncSession):
    presets_dir = Path(__file__).parent.parent / "templates" / "presets"
    for file_path in presets_dir.glob("*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        name = data["name"]
        result = await db.execute(select(Template).where(Template.name == name))
        existing = result.scalar_one_or_none()
        
        if not existing:
            template = Template(
                name=name,
                use_case=data["use_case"],
                variables=data["variables"],
                script=data["script"],
                dtmf_map=data["dtmf_map"],
                speech_enabled=data["speech_enabled"],
                voicemail_policy=data["voicemail_policy"],
                is_preset=True,
            )
            db.add(template)
            print(f"Created preset template: {name}")
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        print(f"Failed to seed templates: {e}")

async def main():
    print("Initializing database...")
    await init_db()
    
    async with AsyncSessionLocal() as session:
        print("Seeding admin user...")
        await seed_admin(session)
        print("Seeding templates...")
        await seed_templates(session)
    
    print("Seeding complete.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
