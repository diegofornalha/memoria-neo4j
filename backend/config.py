#!/usr/bin/env python3
"""
Configurações centralizadas para o backend Neo4j
Todas as credenciais e paths devem vir de variáveis de ambiente
"""
import os
from pathlib import Path

# Diretório base do projeto (relativo ao arquivo config.py)
BASE_DIR = Path(__file__).parent.parent

# Neo4j - NUNCA usar valores hardcoded em produção
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")  # Sem default - força configuração
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Diretórios - relativos ao projeto
BACKUP_DIR = Path(os.getenv("NEO4J_BACKUP_DIR", str(BASE_DIR / "backups")))
BACKUP_DIR.mkdir(exist_ok=True)

# Caminho do script neo4j-query (pode ser customizado via env var)
NEO4J_QUERY_PATH = os.getenv("NEO4J_QUERY_PATH", str(BASE_DIR / "script" / "neo4j-query"))


def validate_config() -> bool:
    """Valida que as configurações essenciais estão definidas"""
    errors = []

    if not NEO4J_PASSWORD:
        errors.append("NEO4J_PASSWORD não está definida. Configure via variável de ambiente.")

    if not Path(NEO4J_QUERY_PATH).exists():
        errors.append(f"neo4j-query não encontrado em: {NEO4J_QUERY_PATH}")

    if errors:
        for error in errors:
            print(f"❌ Config Error: {error}")
        return False

    return True


def get_neo4j_auth() -> tuple:
    """Retorna tupla de autenticação para o driver Neo4j"""
    if not NEO4J_PASSWORD:
        raise ValueError("NEO4J_PASSWORD não configurada. Defina a variável de ambiente.")
    return (NEO4J_USERNAME, NEO4J_PASSWORD)
