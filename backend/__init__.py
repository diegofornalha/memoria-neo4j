"""
Sistema de Backup Seguro para Neo4j
Refatorado com configuracoes centralizadas e seguranca aprimorada
"""

__version__ = "3.0.0"
__author__ = "Claude Code"

from .config import (
    NEO4J_URI,
    NEO4J_USERNAME,
    BACKUP_DIR,
    get_neo4j_auth,
    validate_config
)

from .utils import (
    execute_query,
    safe_get_line,
    parse_query_result,
    get_node_count,
    get_relationship_count
)

from .neo4j_backup_restore import Neo4jBackupRestore

__all__ = [
    "NEO4J_URI",
    "NEO4J_USERNAME",
    "BACKUP_DIR",
    "get_neo4j_auth",
    "validate_config",
    "execute_query",
    "safe_get_line",
    "parse_query_result",
    "get_node_count",
    "get_relationship_count",
    "Neo4jBackupRestore"
]