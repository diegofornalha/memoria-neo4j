#!/usr/bin/env python3
"""
CLI Unificado para Neo4j - Todos os comandos integrados
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import subprocess

# Adicionar o diretório ao path para importar neo4j_backup_restore
sys.path.insert(0, '/Users/2a/.claude/memoria-neo4j')
from neo4j_backup_restore import Neo4jBackupRestore

BACKUP_DIR = Path("/Users/2a/.claude/memoria-neo4j/backups")

def print_header(title, color="cyan"):
    """Imprime cabeçalho colorido"""
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

def execute_query(query):
    """Executa query via neo4j-query"""
    try:
        cmd = ['/Users/2a/.claude/neo4j-query', query]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None

def backup_command(args):
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

def restore_command(args):
    """Comando de restauração"""
    print_header("🔄 Neo4j Restore", "cyan")

    if not args:
        # Listar backups disponíveis
        print("📦 Backups disponíveis:\n")
        backups = sorted(BACKUP_DIR.glob("BACKUP_COMPLETE_*.zip"))

        if not backups:
            print("❌ Nenhum backup encontrado")
            return

        for i, backup in enumerate(backups[-10:], 1):  # Últimos 10
            size_mb = backup.stat().st_size / 1024 / 1024
            print(f"  [{i}] {backup.name} ({size_mb:.2f} MB)")

        print("\nUse: /restore-neo4j <arquivo.zip>")
        return

    backup_file = args[0]

    # Se for apenas nome, procurar no diretório
    if not Path(backup_file).exists():
        backup_file = BACKUP_DIR / backup_file

    neo4j = Neo4jBackupRestore()
    try:
        neo4j.restore_backup(backup_file)
    finally:
        neo4j.close()

def clean_command(args):
    """Comando de limpeza"""
    print_header("🗑️  Neo4j Clean", "yellow")

    # Verificar estado atual
    result = execute_query("MATCH (n) RETURN count(n) as count")
    if result:
        lines = result.strip().split('\n')
        if len(lines) > 1:
            node_count = lines[1]
            print(f"📊 Nós atuais: {node_count}")

    result = execute_query("MATCH ()-[r]->() RETURN count(r) as count")
    if result:
        lines = result.strip().split('\n')
        if len(lines) > 1:
            rel_count = lines[1]
            print(f"📊 Relações atuais: {rel_count}\n")

    # Opções
    if "--dry-run" in args:
        print("🔍 Modo preview (nenhuma alteração será feita)")
        return

    if "--all" in args:
        print("⚠️  ATENÇÃO: Isso removerá TODOS os dados!")
        print("📦 Um backup será criado automaticamente\n")

        confirm = input("Confirmar limpeza total? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Operação cancelada")
            return

        # Criar backup de segurança
        print("\n💾 Criando backup de segurança...")
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

            # Contar nós do tipo
            result = execute_query(f"MATCH (n:Learning {{type: '{node_type}'}}) RETURN count(n) as count")
            if result:
                lines = result.strip().split('\n')
                if len(lines) > 1:
                    count = lines[1]
                    print(f"📊 Nós do tipo '{node_type}': {count}\n")

                    confirm = input(f"Remover todos os nós tipo '{node_type}'? (yes/no): ")
                    if confirm.lower() == 'yes':
                        execute_query(f"MATCH (n:Learning {{type: '{node_type}'}}) DETACH DELETE n")
                        print(f"✅ Nós do tipo '{node_type}' removidos")

    elif "--orphans" in args:
        # Remover nós órfãos
        result = execute_query("MATCH (n) WHERE NOT (n)--() RETURN count(n) as count")
        if result:
            lines = result.strip().split('\n')
            if len(lines) > 1:
                count = lines[1]
                print(f"📊 Nós órfãos encontrados: {count}\n")

                if int(count) > 0:
                    confirm = input("Remover nós órfãos? (yes/no): ")
                    if confirm.lower() == 'yes':
                        execute_query("MATCH (n) WHERE NOT (n)--() DELETE n")
                        print("✅ Nós órfãos removidos")
    else:
        print("Opções disponíveis:")
        print("  --all        : Limpar todo o banco")
        print("  --type <tipo>: Limpar nós de um tipo específico")
        print("  --orphans    : Limpar nós órfãos (sem relações)")
        print("  --dry-run    : Preview sem executar")

def manager_command(args):
    """Comando gerenciador interativo"""
    print_header("🔒 Neo4j Manager", "purple")

    while True:
        print("\n📁 Operações Disponíveis:")
        print("  [1] 📊 Status e Estatísticas")
        print("  [2] 💾 Criar Backup")
        print("  [3] 🔄 Restaurar Backup")
        print("  [4] 🗑️  Limpar Dados")
        print("  [5] 🔍 Consultar Grafo")
        print("  [Q] Sair\n")

        choice = input("Escolha uma opção: ").strip().upper()

        if choice == '1':
            # Status
            print("\n📊 Estatísticas do Grafo:\n")

            result = execute_query("MATCH (n) RETURN count(n) as count")
            if result:
                lines = result.strip().split('\n')
                if len(lines) > 1:
                    print(f"Total de nós: {lines[1]}")

            result = execute_query("MATCH ()-[r]->() RETURN count(r) as count")
            if result:
                lines = result.strip().split('\n')
                if len(lines) > 1:
                    print(f"Total de relações: {lines[1]}")

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
                        print(f"  • {line}")

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
            print("\nOpções de limpeza:")
            print("  1. Limpar tudo")
            print("  2. Limpar por tipo")
            print("  3. Limpar órfãos")

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
            print("\n👋 Até logo!")
            break

def status_command(args):
    """Comando de status rápido"""
    print_header("📊 Neo4j Status", "green")

    # Nós
    result = execute_query("MATCH (n) RETURN count(n) as count")
    if result:
        lines = result.strip().split('\n')
        if len(lines) > 1:
            print(f"📊 Total de nós: {lines[1]}")

    # Relações
    result = execute_query("MATCH ()-[r]->() RETURN count(r) as count")
    if result:
        lines = result.strip().split('\n')
        if len(lines) > 1:
            print(f"🔗 Total de relações: {lines[1]}")

    # Learning nodes
    result = execute_query("MATCH (n:Learning) RETURN count(n) as count")
    if result:
        lines = result.strip().split('\n')
        if len(lines) > 1:
            print(f"🎓 Nós Learning: {lines[1]}")

    # Últimos backups
    print("\n📦 Últimos backups:")
    backups = sorted(BACKUP_DIR.glob("*.zip"))[-3:]
    for backup in backups:
        size_mb = backup.stat().st_size / 1024 / 1024
        print(f"  • {backup.name} ({size_mb:.2f} MB)")

def main():
    """Função principal do CLI"""

    if len(sys.argv) < 2:
        print("Neo4j CLI - Comandos disponíveis:")
        print("  backup   - Criar backup completo")
        print("  restore  - Restaurar backup")
        print("  clean    - Limpar dados")
        print("  manager  - Gerenciador interativo")
        print("  status   - Status rápido")
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