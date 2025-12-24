#!/usr/bin/env python3
"""
CLI Unificado para Neo4j - Todos os comandos integrados
"""
import sys
import json
from pathlib import Path
from typing import List, Optional

# Importar configuracoes e utilitarios centralizados
from config import BACKUP_DIR
from utils import (
    execute_query,
    parse_query_result,
    get_node_count,
    get_relationship_count,
    validate_cypher_identifier,
    sanitize_cypher_identifier,
    sanitize_cypher_string,
    logger
)
from neo4j_backup_restore import Neo4jBackupRestore


def print_header(title: str, color: str = "cyan") -> None:
    """Imprime cabecalho colorido"""
    colors = {
        "cyan": "\033[0;36m",
        "green": "\033[0;32m",
        "yellow": "\033[1;33m",
        "red": "\033[0;31m",
        "purple": "\033[0;35m"
    }
    reset = "\033[0m"
    color_code = colors.get(color, colors["cyan"])

    print(f"{color_code}╔{'═' * 50}╗{reset}")
    print(f"{color_code}║{title.center(50)}║{reset}")
    print(f"{color_code}╚{'═' * 50}╝{reset}\n")


def backup_command(args: List[str]) -> None:
    """Comando de backup"""
    print_header("🔒 Neo4j Backup", "green")

    tag = None
    if args and "--tag" in args:
        idx = args.index("--tag")
        if idx + 1 < len(args):
            tag = args[idx + 1]

    neo4j = Neo4jBackupRestore()
    try:
        result = neo4j.create_backup(tag)
        if result:
            print("\n✅ Use /restore-neo4j para restaurar este backup")
    finally:
        neo4j.close()


def restore_command(args: List[str]) -> None:
    """Comando de restauracao"""
    print_header("🔄 Neo4j Restore", "cyan")

    if not args:
        # Listar backups disponiveis
        print("📦 Backups disponiveis:\n")
        backups = sorted(BACKUP_DIR.glob("BACKUP_COMPLETE_*.zip"))

        if not backups:
            print("❌ Nenhum backup encontrado")
            return

        for i, backup in enumerate(backups[-10:], 1):  # Ultimos 10
            size_mb = backup.stat().st_size / 1024 / 1024
            print(f"  [{i}] {backup.name} ({size_mb:.2f} MB)")

        print("\nUse: /restore-neo4j <arquivo.zip>")
        return

    backup_file = args[0]

    # Se for apenas nome, procurar no diretorio
    if not Path(backup_file).exists():
        backup_file = str(BACKUP_DIR / backup_file)

    neo4j = Neo4jBackupRestore()
    try:
        neo4j.restore_backup(backup_file)
    finally:
        neo4j.close()


def clean_command(args: List[str]) -> None:
    """Comando de limpeza"""
    print_header("🗑️  Neo4j Clean", "yellow")

    # Verificar estado atual usando funcoes do utils
    node_count = get_node_count()
    rel_count = get_relationship_count()

    print(f"📊 Nos atuais: {node_count}")
    print(f"📊 Relacoes atuais: {rel_count}\n")

    # Opcoes
    if "--dry-run" in args:
        print("🔍 Modo preview (nenhuma alteracao sera feita)")
        return

    if "--all" in args:
        print("⚠️  ATENCAO: Isso removera TODOS os dados!")
        print("📦 Um backup sera criado automaticamente\n")

        confirm = input("Confirmar limpeza total? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Operacao cancelada")
            return

        # Criar backup de seguranca
        print("\n💾 Criando backup de seguranca...")
        neo4j = Neo4jBackupRestore()
        try:
            neo4j.create_backup("pre_clean")
        finally:
            neo4j.close()

        # Limpar tudo
        print("\n🗑️  Limpando banco...")
        execute_query("MATCH ()-[r]->() DELETE r")
        execute_query("MATCH (n) DELETE n")
        print("✅ Banco limpo completamente")

    elif "--type" in args:
        idx = args.index("--type")
        if idx + 1 < len(args):
            node_type = args[idx + 1]

            # Sanitizar usando funcao apropriada do utils
            # Usa sanitize_cypher_string para valores de propriedade
            safe_type = sanitize_cypher_string(node_type)

            # Validar que o tipo nao esta vazio apos sanitizacao
            if not safe_type or safe_type == node_type and not validate_cypher_identifier(node_type):
                # Se contem caracteres especiais que nao sao alfanumericos em posicao de valor
                # a sanitizacao ja tratou, entao podemos prosseguir
                pass

            result = execute_query(f"MATCH (n:Learning {{type: '{safe_type}'}}) RETURN count(n) as count")
            count = parse_query_result(result)

            if count:
                print(f"📊 Nos do tipo '{node_type}': {count}\n")

                confirm = input(f"Remover todos os nos tipo '{node_type}'? (yes/no): ")
                if confirm.lower() == 'yes':
                    execute_query(f"MATCH (n:Learning {{type: '{safe_type}'}}) DETACH DELETE n")
                    print(f"✅ Nos do tipo '{node_type}' removidos")

    elif "--orphans" in args:
        # Remover nos orfaos
        result = execute_query("MATCH (n) WHERE NOT (n)--() RETURN count(n) as count")
        count = parse_query_result(result)

        if count:
            print(f"📊 Nos orfaos encontrados: {count}\n")

            try:
                count_int = int(count)
                if count_int > 0:
                    confirm = input("Remover nos orfaos? (yes/no): ")
                    if confirm.lower() == 'yes':
                        execute_query("MATCH (n) WHERE NOT (n)--() DELETE n")
                        print("✅ Nos orfaos removidos")
            except ValueError:
                pass
    else:
        print("Opcoes disponiveis:")
        print("  --all        : Limpar todo o banco")
        print("  --type <tipo>: Limpar nos de um tipo especifico")
        print("  --orphans    : Limpar nos orfaos (sem relacoes)")
        print("  --dry-run    : Preview sem executar")


def manager_command(args: List[str]) -> None:
    """Comando gerenciador interativo"""
    print_header("🔒 Neo4j Manager", "purple")

    while True:
        print("\n📁 Operacoes Disponiveis:")
        print("  [1] 📊 Status e Estatisticas")
        print("  [2] 💾 Criar Backup")
        print("  [3] 🔄 Restaurar Backup")
        print("  [4] 🗑️  Limpar Dados")
        print("  [5] 🔍 Consultar Grafo")
        print("  [Q] Sair\n")

        choice = input("Escolha uma opcao: ").strip().upper()

        if choice == '1':
            # Status usando funcoes do utils
            print("\n📊 Estatisticas do Grafo:\n")
            print(f"Total de nos: {get_node_count()}")
            print(f"Total de relacoes: {get_relationship_count()}")

            result = execute_query("""
                MATCH (n:Learning)
                RETURN n.type as type, count(n) as count
                ORDER BY count DESC
                LIMIT 5
            """)
            if result:
                print("\nTop 5 tipos:")
                lines = result.strip().split('\n')[1:]
                for line in lines[:5]:
                    if line:
                        print(f"  - {line}")

        elif choice == '2':
            # Backup
            tag = input("Tag para o backup (opcional): ").strip()
            neo4j = Neo4jBackupRestore()
            try:
                neo4j.create_backup(tag if tag else None)
            finally:
                neo4j.close()

        elif choice == '3':
            # Restaurar
            restore_command([])
            file_name = input("\nNome do arquivo: ").strip()
            if file_name:
                restore_command([file_name])

        elif choice == '4':
            # Limpar
            print("\nOpcoes de limpeza:")
            print("  1. Limpar tudo")
            print("  2. Limpar por tipo")
            print("  3. Limpar orfaos")

            clean_choice = input("Escolha: ").strip()

            if clean_choice == '1':
                clean_command(['--all'])
            elif clean_choice == '2':
                tipo = input("Digite o tipo: ").strip()
                clean_command(['--type', tipo])
            elif clean_choice == '3':
                clean_command(['--orphans'])

        elif choice == '5':
            # Consultar
            query = input("Query Cypher: ").strip()
            if query:
                result = execute_query(query)
                if result:
                    print(f"\n{result}")

        elif choice == 'Q':
            print("\n👋 Ate logo!")
            break


def status_command(args: List[str]) -> None:
    """Comando de status rapido"""
    print_header("📊 Neo4j Status", "green")

    # Usar funcoes do utils
    print(f"📊 Total de nos: {get_node_count()}")
    print(f"🔗 Total de relacoes: {get_relationship_count()}")

    # Learning nodes
    result = execute_query("MATCH (n:Learning) RETURN count(n) as count")
    learning_count = parse_query_result(result)
    if learning_count:
        print(f"🎓 Nos Learning: {learning_count}")

    # Ultimos backups
    print("\n📦 Ultimos backups:")
    backups = sorted(BACKUP_DIR.glob("*.zip"))[-3:]
    for backup in backups:
        size_mb = backup.stat().st_size / 1024 / 1024
        print(f"  - {backup.name} ({size_mb:.2f} MB)")


def main() -> None:
    """Funcao principal do CLI"""
    if len(sys.argv) < 2:
        print("Neo4j CLI - Comandos disponiveis:")
        print("  backup   - Criar backup completo")
        print("  restore  - Restaurar backup")
        print("  clean    - Limpar dados")
        print("  manager  - Gerenciador interativo")
        print("  status   - Status rapido")
        return

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        'backup': backup_command,
        'restore': restore_command,
        'clean': clean_command,
        'manager': manager_command,
        'status': status_command
    }

    if command in commands:
        commands[command](args)
    else:
        print(f"❌ Comando desconhecido: {command}")
        print("Use: backup, restore, clean, manager, status")


if __name__ == "__main__":
    main()
