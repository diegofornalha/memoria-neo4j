#!/usr/bin/env python3
"""
Utilitarios compartilhados para o backend Neo4j
Funcoes comuns extraidas para evitar duplicacao
"""
import subprocess
import re
import logging
from typing import Optional, List, Any
from pathlib import Path

from config import NEO4J_QUERY_PATH

# Logger do modulo (SEM basicConfig global - deixar para o caller configurar)
logger = logging.getLogger(__name__)

# Regex para validacao de identificadores Cypher
VALID_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def execute_query(query: str, timeout: int = 30) -> Optional[str]:
    """
    Executa query via neo4j-query CLI

    Args:
        query: Query Cypher a executar
        timeout: Timeout em segundos (default 30)

    Returns:
        Output da query ou None se falhar
    """
    try:
        cmd = [NEO4J_QUERY_PATH, query]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            logger.error(f"Query falhou: {result.stderr}")
            return None

        return result.stdout

    except subprocess.TimeoutExpired:
        logger.error(f"Query timeout apos {timeout} segundos")
        return None
    except FileNotFoundError:
        logger.error(f"neo4j-query nao encontrado em: {NEO4J_QUERY_PATH}")
        return None
    except Exception as e:
        logger.error(f"Erro executando query: {e}")
        return None


def safe_get_line(text: Optional[str], index: int, default: str = "0") -> str:
    """
    Obtem linha especifica de texto de forma segura

    Args:
        text: Texto com multiplas linhas (pode ser None)
        index: Indice da linha desejada (0-based)
        default: Valor padrao se indice nao existir

    Returns:
        Linha no indice ou valor default
    """
    if text is None or not text.strip():
        return default

    lines = text.strip().split('\n')

    if index < 0 or index >= len(lines):
        return default

    return lines[index].strip()


def parse_query_result(result: Optional[str], line_index: int = 1) -> Optional[str]:
    """
    Parse resultado de query do Neo4j (pula header na linha 0)

    Args:
        result: Output da query
        line_index: Indice da linha com dados (default 1, apos header)

    Returns:
        Valor da linha ou None
    """
    if not result:
        return None
    return safe_get_line(result, line_index)


def get_node_count() -> int:
    """Obtem contagem total de nos"""
    result = execute_query("MATCH (n) RETURN count(n) as count")
    value = parse_query_result(result)
    try:
        return int(value) if value else 0
    except ValueError:
        logger.warning(f"Valor invalido para node count: {value}")
        return 0


def get_relationship_count() -> int:
    """Obtem contagem total de relacionamentos"""
    result = execute_query("MATCH ()-[r]->() RETURN count(r) as count")
    value = parse_query_result(result)
    try:
        return int(value) if value else 0
    except ValueError:
        logger.warning(f"Valor invalido para rel count: {value}")
        return 0


def validate_cypher_identifier(identifier: str) -> bool:
    """
    Valida se um identificador eh seguro para uso em Cypher

    Labels e tipos de relacao devem comecar com letra ou underscore
    e conter apenas alfanumericos e underscore.
    """
    if not identifier:
        return False
    return bool(VALID_IDENTIFIER_PATTERN.match(identifier))


def sanitize_cypher_identifier(identifier: str, default: str = "Node") -> str:
    """
    Sanitiza identificador removendo caracteres invalidos

    Args:
        identifier: String a sanitizar
        default: Valor padrao se resultado for vazio

    Returns:
        Identificador seguro para Cypher
    """
    if not identifier:
        return default

    # Remove caracteres nao alfanumericos (exceto underscore)
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', identifier)

    # Garante que comeca com letra ou underscore
    if sanitized and sanitized[0].isdigit():
        sanitized = '_' + sanitized

    return sanitized or default


def sanitize_cypher_string(value: str) -> str:
    """
    Sanitiza string para uso em queries Cypher
    NOTA: Preferir usar parametros do driver ao inves desta funcao

    Args:
        value: String a sanitizar

    Returns:
        String com caracteres especiais escapados
    """
    if not isinstance(value, str):
        return str(value)

    # Escape de aspas simples, duplas e backslash
    return value.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')


def format_properties_for_cypher(props: dict) -> str:
    """
    Formata dicionario de propriedades para query Cypher
    NOTA: Preferir usar parametros do driver quando possivel

    Args:
        props: Dicionario de propriedades

    Returns:
        String formatada para Cypher {key: 'value', ...}
    """
    if not props:
        return "{}"

    formatted = []
    for key, value in props.items():
        # Validar nome da chave
        if not validate_cypher_identifier(key):
            safe_key = sanitize_cypher_identifier(key, default="prop")
            logger.warning(f"Chave sanitizada: {key} -> {safe_key}")
            key = safe_key

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
            # Processar listas
            safe_items = []
            for item in value:
                if item is None:
                    continue
                elif isinstance(item, str):
                    safe_items.append(f"'{sanitize_cypher_string(item)}'")
                elif isinstance(item, (int, float, bool)):
                    safe_items.append(str(item).lower() if isinstance(item, bool) else str(item))
                else:
                    # Converter outros tipos para string
                    safe_items.append(f"'{sanitize_cypher_string(str(item))}'")
            formatted.append(f"{key}: [{', '.join(safe_items)}]")
        elif isinstance(value, dict):
            # Dicts nao sao suportados diretamente, converter para string JSON
            import json
            safe_value = sanitize_cypher_string(json.dumps(value))
            formatted.append(f"{key}: '{safe_value}'")
        else:
            # Fallback para outros tipos
            safe_value = sanitize_cypher_string(str(value))
            formatted.append(f"{key}: '{safe_value}'")

    return "{" + ", ".join(formatted) + "}"
