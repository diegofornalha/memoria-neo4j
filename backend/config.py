#!/usr/bin/env python3
"""
Configuracoes centralizadas para o backend Neo4j
Todas as credenciais e paths devem vir de variaveis de ambiente
"""
import os
import logging
from pathlib import Path
from typing import Tuple

# Logger do modulo
logger = logging.getLogger(__name__)

# Diretorio base do projeto (relativo ao arquivo config.py)
BASE_DIR = Path(__file__).parent.parent

# Neo4j - NUNCA usar valores hardcoded em producao
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")  # Sem default - forca configuracao
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Diretorios - relativos ao projeto
_backup_dir_str = os.getenv("NEO4J_BACKUP_DIR", str(BASE_DIR / "backups"))
BACKUP_DIR = Path(_backup_dir_str)

# Caminho do script neo4j-query (pode ser customizado via env var)
NEO4J_QUERY_PATH = os.getenv("NEO4J_QUERY_PATH", str(BASE_DIR / "script" / "neo4j-query"))


def _ensure_backup_dir() -> bool:
    """
    Cria diretorio de backup com verificacao de permissoes

    Returns:
        True se diretorio existe/foi criado e tem permissao de escrita
    """
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        # Verificar permissao de escrita
        test_file = BACKUP_DIR / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
            return True
        except PermissionError:
            logger.error(f"Sem permissao de escrita em: {BACKUP_DIR}")
            return False
        except Exception as e:
            logger.warning(f"Erro ao testar escrita em {BACKUP_DIR}: {e}")
            # Assume que esta ok se mkdir funcionou
            return True

    except PermissionError:
        logger.error(f"Sem permissao para criar diretorio: {BACKUP_DIR}")
        return False
    except Exception as e:
        logger.error(f"Erro ao criar diretorio de backup: {e}")
        return False


# Inicializar diretorio de backup com verificacao
_backup_dir_ok = _ensure_backup_dir()
if not _backup_dir_ok:
    print(f"⚠️  AVISO: Problemas com diretorio de backup: {BACKUP_DIR}")


def validate_config() -> bool:
    """
    Valida que as configuracoes essenciais estao definidas

    Returns:
        True se todas as configuracoes estao validas
    """
    errors = []

    if not NEO4J_PASSWORD:
        errors.append("NEO4J_PASSWORD nao esta definida. Configure via variavel de ambiente.")

    if not Path(NEO4J_QUERY_PATH).exists():
        errors.append(f"neo4j-query nao encontrado em: {NEO4J_QUERY_PATH}")

    if not _backup_dir_ok:
        errors.append(f"Diretorio de backup inacessivel: {BACKUP_DIR}")

    if errors:
        for error in errors:
            print(f"❌ Config Error: {error}")
            logger.error(f"Config validation failed: {error}")
        return False

    return True


def get_neo4j_auth() -> Tuple[str, str]:
    """
    Retorna tupla de autenticacao para o driver Neo4j

    Returns:
        Tupla (username, password)

    Raises:
        ValueError: Se NEO4J_PASSWORD nao estiver configurada
    """
    if not NEO4J_PASSWORD:
        raise ValueError("NEO4J_PASSWORD nao configurada. Defina a variavel de ambiente.")
    return (NEO4J_USERNAME, NEO4J_PASSWORD)


def get_backup_dir() -> Path:
    """
    Retorna diretorio de backup verificado

    Returns:
        Path do diretorio de backup

    Raises:
        RuntimeError: Se diretorio nao esta acessivel
    """
    if not _backup_dir_ok:
        raise RuntimeError(f"Diretorio de backup nao esta acessivel: {BACKUP_DIR}")
    return BACKUP_DIR
