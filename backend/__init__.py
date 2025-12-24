"""
Sistema de Backup Seguro para Neo4j
Versao 3.1 - Com correcoes de seguranca e performance
"""

__version__ = "3.1.0"
__author__ = "Claude Code"

from .config import (
    NEO4J_URI,
    NEO4J_USERNAME,
    BACKUP_DIR,
    get_neo4j_auth,
    get_backup_dir,
    validate_config
)

from .utils import (
    execute_query,
    safe_get_line,
    parse_query_result,
    get_node_count,
    get_relationship_count,
    validate_cypher_identifier,
    sanitize_cypher_identifier,
    sanitize_cypher_string
)

from .neo4j_backup_restore import (
    Neo4jBackupRestore,
    Neo4jConnectionError,
    Neo4jConfigError,
    BackupValidationError
)

__all__ = [
    # Config
    "NEO4J_URI",
    "NEO4J_USERNAME",
    "BACKUP_DIR",
    "get_neo4j_auth",
    "get_backup_dir",
    "validate_config",
    # Utils
    "execute_query",
    "safe_get_line",
    "parse_query_result",
    "get_node_count",
    "get_relationship_count",
    "validate_cypher_identifier",
    "sanitize_cypher_identifier",
    "sanitize_cypher_string",
    # Classes
    "Neo4jBackupRestore",
    "Neo4jConnectionError",
    "Neo4jConfigError",
    "BackupValidationError"
]