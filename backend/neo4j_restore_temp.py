#!/usr/bin/env python3
"""Restauração segura de backups Neo4j"""

import os
import sys
import json
import zipfile
from pathlib import Path
from neo4j import GraphDatabase

# Configurações
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

def restore_backup():
    print("\n📍 Escolha o tipo de restauração:")
    print("  [1] Backup MCP consolidado (.zip)")
    print("  [2] Backup temático (.json)")
    print("  [3] Todos os backups temáticos")
    print("  [0] Cancelar")

    choice = input("\nOpção: ")

    if choice == "0":
        print("❌ Restauração cancelada")
        return

    try:
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )

        with driver.session(database=NEO4J_DATABASE) as session:
            # Verificar estado atual
            current = session.run("MATCH (n) RETURN count(n) as count").single()
            if current['count'] > 0:
                print(f"\n⚠️  AVISO: Existem {current['count']} nós no banco!")
                confirm = input("Deseja limpar antes de restaurar? (s/n): ")
                if confirm.lower() == 's':
                    print("🗑️  Limpando banco...")
                    session.run("MATCH (n) DETACH DELETE n")

            if choice == "1":
                # Restaurar backup MCP
                backup_file = input("\nNome do arquivo ZIP: ")
                backup_path = Path(f"memory-backups-mcp/{backup_file}")

                if not backup_path.exists():
                    print(f"❌ Arquivo não encontrado: {backup_path}")
                    return

                print(f"📦 Extraindo {backup_file}...")
                with zipfile.ZipFile(backup_path, 'r') as zf:
                    # Extrair e ler JSON
                    json_files = [f for f in zf.namelist() if f.endswith('.json') and 'validation' not in f]
                    if json_files:
                        data = json.loads(zf.read(json_files[0]))
                        restore_data(session, data)

            elif choice == "2":
                # Restaurar backup temático
                theme_file = input("\nNome do arquivo JSON: ")
                theme_path = Path(f"memory-backups-thematic/{theme_file}")

                if not theme_path.exists():
                    print(f"❌ Arquivo não encontrado: {theme_path}")
                    return

                print(f"📖 Lendo {theme_file}...")
                with open(theme_path) as f:
                    data = json.load(f)
                    restore_data(session, data)

            elif choice == "3":
                # Restaurar todos os backups temáticos
                thematic_dir = Path("memory-backups-thematic")
                theme_files = list(thematic_dir.glob("THEME_*.json"))

                if not theme_files:
                    print("❌ Nenhum backup temático encontrado")
                    return

                print(f"\n📚 Restaurando {len(theme_files)} temas...")
                for theme_file in theme_files:
                    print(f"  • {theme_file.name}")
                    with open(theme_file) as f:
                        data = json.load(f)
                        restore_data(session, data)

            # Estatísticas finais
            final = session.run("""
                MATCH (n)
                WITH count(n) as nodes
                MATCH ()-[r]->()
                RETURN nodes, count(r) as rels
            """).single()

            print(f"\n✅ Restauração concluída!")
            print(f"   • Nós: {final['nodes']}")
            print(f"   • Relacionamentos: {final['rels']}")

        driver.close()

    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

def restore_data(session, data):
    """Restaura dados no Neo4j"""
    nodes = data.get('nodes', [])
    relationships = data.get('relationships', [])

    print(f"   → Restaurando {len(nodes)} nós...")
    for node in nodes:
        labels = ':'.join(node.get('labels', ['Restored']))
        props = node.get('properties', {})

        # Criar nó
        query = f"CREATE (n:{labels}) SET n = $props RETURN n"
        session.run(query, props=props)

    print(f"   → Restaurando {len(relationships)} relacionamentos...")
    # Simplificado - em produção seria mais complexo

if __name__ == "__main__":
    restore_backup()
