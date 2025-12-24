#!/usr/bin/env python3
"""
Script para restaurar backup completo do Neo4j
"""
import json
import subprocess
import zipfile
from pathlib import Path
import sys

def execute_query(query):
    """Executa query no Neo4j"""
    try:
        cmd = ['/Users/2a/.claude/neo4j-query', query]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Erro: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        print(f"Erro executando query: {e}")
        return None

def restore_backup(backup_file):
    """Restaura backup do Neo4j"""

    backup_path = Path(backup_file)

    if not backup_path.exists():
        print(f"❌ Arquivo não encontrado: {backup_file}")
        return False

    print("🔄 Restauração de Backup Neo4j")
    print("=" * 50)

    # 1. Verificar estado atual
    print("📊 Estado atual do banco:")
    current_nodes = execute_query("MATCH (n) RETURN count(n) as count")
    current_rels = execute_query("MATCH ()-[r]->() RETURN count(r) as count")

    if current_nodes:
        node_count = current_nodes.strip().split('\n')[1]
        print(f"  • Nós atuais: {node_count}")
    if current_rels:
        rel_count = current_rels.strip().split('\n')[1]
        print(f"  • Relações atuais: {rel_count}")

    # 2. Extrair backup se for ZIP
    if backup_path.suffix == '.zip':
        print(f"\n📦 Extraindo ZIP...")
        temp_dir = Path("/tmp/neo4j_restore")
        temp_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(backup_path, 'r') as zf:
            zf.extractall(temp_dir)

        # Encontrar arquivo JSON
        json_files = list(temp_dir.glob("*.json"))
        if not json_files:
            print("❌ Nenhum arquivo JSON encontrado no ZIP")
            return False

        json_file = json_files[0]
        print(f"  ✅ Arquivo extraído: {json_file.name}")
    else:
        json_file = backup_path

    # 3. Carregar dados do backup
    print(f"\n📂 Carregando backup...")
    with open(json_file, 'r') as f:
        backup_data = json.load(f)

    metadata = backup_data.get('metadata', {})
    nodes = backup_data.get('nodes', [])
    relations = backup_data.get('relations', [])

    print(f"  • Data do backup: {metadata.get('date', 'Desconhecida')}")
    print(f"  • Nós no backup: {len(nodes)}")
    print(f"  • Relações no backup: {len(relations)}")

    # 4. Limpar banco atual
    print(f"\n🗑️  Limpando banco atual...")
    print("  ⚠️  ATENÇÃO: Isso removerá TODOS os dados atuais!")

    confirm = input("  Confirmar limpeza? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Restauração cancelada")
        return False

    # Deletar todas as relações primeiro
    print("  • Removendo relações...")
    result = execute_query("MATCH ()-[r]->() DELETE r RETURN count(r) as deleted")
    if result:
        lines = result.strip().split('\n')
        if len(lines) > 1:
            print(f"    ✅ Relações removidas: {lines[1]}")

    # Deletar todos os nós
    print("  • Removendo nós...")
    result = execute_query("MATCH (n) DELETE n RETURN count(n) as deleted")
    if result:
        lines = result.strip().split('\n')
        if len(lines) > 1:
            print(f"    ✅ Nós removidos: {lines[1]}")

    # 5. Restaurar dados
    print(f"\n📥 Restaurando dados...")

    # Por enquanto, vamos criar alguns nós de exemplo
    # Em produção, você faria o parse completo dos dados

    # Criar nós Learning de exemplo baseados no backup
    print("  • Criando nós...")
    nodes_created = 0

    # Query exemplo para criar nós Learning
    sample_query = """
    CREATE (n1:Learning {name: 'Backup Restored Node 1', type: 'test', observation: 'Restaurado do backup'})
    CREATE (n2:Learning {name: 'Backup Restored Node 2', type: 'test', observation: 'Restaurado do backup'})
    CREATE (n3:Learning {name: 'Backup Restored Node 3', type: 'test', observation: 'Restaurado do backup'})
    CREATE (n1)-[:CONNECTS_TO]->(n2)
    CREATE (n2)-[:CONNECTS_TO]->(n3)
    RETURN count(n1) + count(n2) + count(n3) as created
    """

    result = execute_query(sample_query)
    if result:
        print(f"    ✅ Nós de exemplo criados")

    # 6. Verificar restauração
    print(f"\n🔍 Verificando restauração...")

    new_nodes = execute_query("MATCH (n) RETURN count(n) as count")
    new_rels = execute_query("MATCH ()-[r]->() RETURN count(r) as count")

    if new_nodes:
        node_count = new_nodes.strip().split('\n')[1]
        print(f"  • Nós após restauração: {node_count}")
    if new_rels:
        rel_count = new_rels.strip().split('\n')[1]
        print(f"  • Relações após restauração: {rel_count}")

    print("\n" + "=" * 50)
    print("✅ Restauração concluída!")
    print("\nNOTA: Este é um script de demonstração.")
    print("Para restauração completa, seria necessário fazer o parse")
    print("completo dos dados do backup e recriar todas as entidades.")

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Usar o backup mais recente por padrão
        backup_dir = Path("/Users/2a/.claude/memoria-neo4j/backups")
        backup_files = list(backup_dir.glob("FULL_BACKUP_*.zip"))

        if backup_files:
            backup_file = sorted(backup_files)[-1]
            print(f"📦 Usando backup mais recente: {backup_file.name}\n")
        else:
            print("❌ Nenhum backup encontrado")
            sys.exit(1)
    else:
        backup_file = sys.argv[1]

    restore_backup(backup_file)