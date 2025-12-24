#!/usr/bin/env python3
"""
Utilitários compartilhados para o backend Neo4j
Funções comuns extraídas para evitar duplicação
"""
import subprocess
import logging
from typing import Optional, List, Any
from pathlib import Path

from config import NEO4J_QUERY_PATH

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def execute_query(query: str) -> Optional[str]:
    """
    Executa query via neo4j-query CLI

    Args:
        query: Query Cypher a executar

    Returns:
        Output da query ou None se falhar
    """
    try:
        cmd = [NEO4J_QUERY_PATH, query]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            logger.error(f"Query falhou: {result.stderr}")
            return None

        return result.stdout

    except subprocess.TimeoutExpired:
        logger.error("Query timeout após 30 segundos")
        return None
    except FileNotFoundError:
        logger.error(f"neo4j-query não encontrado em: {NEO4J_QUERY_PATH}")
        return None
    except Exception as e:
        logger.error(f"Erro executando query: {e}")
        return None


def safe_get_line(text: str, index: int, default: str = "0") -> str:
    """
    Obtém linha específica de texto de forma segura

    Args:
        text: Texto com múltiplas linhas
        index: Índice da linha desejada (0-based)
        default: Valor padrão se índice não existir

    Returns:
        Linha no índice ou valor default
    """
    if not text:
        return default

    lines = text.strip().split('\n')

    if index < 0 or index >= len(lines):
        return default

    return lines[index].strip()


def parse_query_result(result: str, line_index: int = 1) -> Optional[str]:
    """
    Parse resultado de query do Neo4j (pula header na linha 0)

    Args:
        result: Output da query
        line_index: Índice da linha com dados (default 1, após header)

    Returns:
        Valor da linha ou None
    """
    if not result:
        return None
    return safe_get_line(result, line_index)


def get_node_count() -> int:
    """Obtém contagem total de nós"""
    result = execute_query("MATCH (n) RETURN count(n) as count")
    value = parse_query_result(result)
    try:
        return int(value) if value else 0
    except ValueError:
        return 0


def get_relationship_count() -> int:
    """Obtém contagem total de relacionamentos"""
    result = execute_query("MATCH ()-[r]->() RETURN count(r) as count")
    value = parse_query_result(result)
    try:
        return int(value) if value else 0
    except ValueError:
        return 0


def sanitize_cypher_string(value: str) -> str:
    """
    Sanitiza string para uso em queries Cypher
    NOTA: Preferir usar parâmetros do driver ao invés desta função

    Args:
        value: String a sanitizar

    Returns:
        String com caracteres especiais escapados
    """
    if not isinstance(value, str):
        return str(value)

    # Escape de aspas simples e caracteres especiais
    return value.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')


def format_properties_for_cypher(props: dict) -> str:
    """
    Formata dicionário de propriedades para query Cypher
    NOTA: Preferir usar parâmetros do driver quando possível

    Args:
        props: Dicionário de propriedades

    Returns:
        String formatada para Cypher {key: 'value', ...}
    """
    if not props:
        return "{}"

    formatted = []
    for key, value in props.items():
        if value is None:
            continue
        elif isinstance(value, str):
            safe_value = sanitize_cypher_string(value)
            formatted.append(f"{key}: '{safe_value}'")
        elif isinstance(value, bool):
            formatted.append(f"{key}: {str(value).lower()}")
        elif isinstance(value, (int, float)):
            formatted.append(f"{key}: {value}")
        elif isinstance(value, list):
            # Listas de strings
            safe_items = [f"'{sanitize_cypher_string(str(item))}'" for item in value]
            formatted.append(f"{key}: [{', '.join(safe_items)}]")

    return "{" + ", ".join(formatted) + "}"
