import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

# Ajuste os imports abaixo conforme a estrutura do seu projeto
from backend.app.model.models import User
from backend.app.enum import UserRole
from backend.app.core.security import hash_password  # Ajuste o caminho se necessário

async def main():
    # Puxa a URL do banco (fallback para localhost se rodar no seu venv Windows)
    db_url = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://nexusflow:nexusflow_dev_local@localhost:5432/nexusflow_dev"
    )
    
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        email_admin = "admin@nexusflow.com"
        
        # Verifica se o usuário já existe para evitar erros
        stmt = select(User).where(User.email == email_admin)
        resultado = await session.execute(stmt)
        usuario_existente = resultado.scalar_one_or_none()
        
        if usuario_existente:
            print(f"O usuário {email_admin} já existe no banco.")
            return

        # Cria o novo usuário
        novo_usuario = User(
            email=email_admin,
            senha_hash=hash_password("123456"),
            papel=UserRole.admin,
            ativo=True
        )
        
        session.add(novo_usuario)
        await session.commit()
        print(f"SUCESSO: Usuário {email_admin} criado com a senha '123456'.")

if __name__ == "__main__":
    asyncio.run(main())