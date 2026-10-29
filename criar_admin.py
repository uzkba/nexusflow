import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.core.security import hash_password
from backend.app.enum import UserRole
from backend.app.model.models import User

MIN_SENHA = 12


async def main() -> int:
    db_url = os.environ.get("DATABASE_URL")
    email = os.environ.get("ADMIN_EMAIL", "").strip()
    senha = os.environ.get("ADMIN_PASSWORD", "")

    if not db_url:
        print("ERRO: DATABASE_URL não definida.")
        return 1
    if not email or "@" not in email:
        print("ERRO: defina ADMIN_EMAIL com um e-mail válido.")
        return 1
    if len(senha) < MIN_SENHA:
        print(f"ERRO: ADMIN_PASSWORD precisa ter pelo menos {MIN_SENHA} caracteres.")
        return 1

    engine = create_async_engine(db_url)
    try:
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            result = await session.execute(select(User).where(User.email == email))
            if result.scalar_one_or_none():
                print(f"O usuário {email} já existe. Nada foi alterado.")
                return 0

            session.add(
                User(
                    email=email,
                    senha_hash=hash_password(senha),
                    papel=UserRole.admin,
                    ativo=True,
                )
            )
            await session.commit()
            print(f"SUCESSO: admin {email} criado.")
            return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
