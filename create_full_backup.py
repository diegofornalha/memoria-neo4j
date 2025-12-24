#!/usr/bin/env python3
"""
Script para criar backup completo do Neo4j
"""
import json
import subprocess
import hashlib
import zipfile
from datetime import datetime
from pathlib import Path

def execute_query(query):
    """Executa query no Neo4j e retorna resultado"""
    try:
        cmd = ['/Users/2a/.claude/neo4j-query', query]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        print(f"Erro executando query: {e}")
        return None

def create_full_backup():
    """Cria backup completo do Neo4j"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("/Users/2a/.claude/memoria-neo4j/backups")
    backup_dir.mkdir(exist_ok=True)

    print("🔒 Neo4j Full Backup")
    print("=" * 50)

    # 1. Exportar todos os nós
    print("📊 Exportando nós...")

    # Query para obter todos os nós com suas propriedades
    nodes_query = """
    MATCH (n)
    RETURN id(n) as id,
           labels(n) as labels,
           properties(n) as properties
    """

    nodes_result = execute_query(nodes_query)
    nodes_data = []

    if nodes_result:
        lines = nodes_result.strip().split('\n')[1:]  # Pular header
        for line in lines:
            if line:
                # Parse manual do resultado CSV
                nodes_data.append({"raw": line})

    print(f"  ✅ {len(nodes_data)} nós encontrados")

    # 2. Exportar todas as relações
    print("🔗 Exportando relações...")

    relations_query = """
    MATCH (a)-[r]->(b)
    RETURN id(a) as source_id,
           id(b) as target_id,
           type(r) as type,
           properties(r) as properties
    """

    relations_result = execute_query(relations_query)
    relations_data = []

    if relations_result:
        lines = relations_result.strip().split('\n')[1:]  # Pular header
        for line in lines:
            if line:
                relations_data.append({"raw": line})

    print(f"  ✅ {len(relations_data)} relações encontradas")

    # 3. Criar estrutura do backup
    backup_data = {
        "metadata": {
            "timestamp": timestamp,
            "date": datetime.now().isoformat(),
            "method": "full_export",
            "version": "2.0",
            "stats": {
                "total_nodes": len(nodes_data),
                "total_relations": len(relations_data),
                "learning_nodes": 0,  # Será atualizado
            }
        },
        "nodes": nodes_data,
        "relations": relations_data
    }

    # Contar nós Learning
    learning_count_result = execute_query("MATCH (n:Learning) RETURN count(n) as count")
    if learning_count_result:
        try:
            count_line = learning_count_result.strip().split('\n')[1]
            backup_data["metadata"]["stats"]["learning_nodes"] = int(count_line)
        except:
            pass

    # 4. Salvar JSON
    json_file = backup_dir / f"FULL_BACKUP_{timestamp}.json"

    print(f"💾 Salvando backup...")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)

    print(f"  ✅ Arquivo: {json_file}")
    print(f"  📊 Tamanho: {json_file.stat().st_size / 1024:.2f} KB")

    # 5. Gerar hash SHA256
    print("🔐 Gerando hash SHA256...")
    with open(json_file, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    hash_file = backup_dir / f"FULL_BACKUP_{timestamp}.sha256"
    with open(hash_file, 'w') as f:
        f.write(f"{file_hash}  {json_file.name}\n")

    print(f"  ✅ Hash: {file_hash[:16]}...")

    # 6. Criar ZIP
    print("📦 Comprimindo backup...")
    zip_file = backup_dir / f"FULL_BACKUP_{timestamp}.zip"

    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(json_file, json_file.name)
        zf.write(hash_file, hash_file.name)

    compressed_size = zip_file.stat().st_size
    compression_ratio = (1 - compressed_size / json_file.stat().st_size) * 100

    print(f"  ✅ ZIP: {zip_file.name}")
    print(f"  📊 Compressão: {compression_ratio:.1f}%")

    # 7. Log do backup
    log_file = backup_dir / "BACKUP_LOG.json"
    log_entry = {
        "timestamp": timestamp,
        "date": datetime.now().isoformat(),
        "file": json_file.name,
        "zip": zip_file.name,
        "hash": file_hash,
        "size_bytes": json_file.stat().st_size,
        "compressed_bytes": compressed_size,
        "nodes": len(nodes_data),
        "relations": len(relations_data),
        "method": "full_export"
    }

    # Adicionar ao log
    if log_file.exists():
        with open(log_file, 'r') as f:
            log_data = json.load(f)
    else:
        log_data = []

    log_data.append(log_entry)

    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2)

    print("\n" + "=" * 50)
    print("✅ BACKUP COMPLETO FINALIZADO!")
    print(f"""
📊 Resumo Final:
  • Nós exportados: {len(nodes_data)}
  • Relações exportadas: {len(relations_data)}
  • Arquivo JSON: {json_file.stat().st_size / 1024:.2f} KB
  • Arquivo ZIP: {compressed_size / 1024:.2f} KB
  • Compressão: {compression_ratio:.1f}%
  • Hash SHA256: {file_hash[:32]}...

📁 Arquivos criados:
  • {json_file.name}
  • {hash_file.name}
  • {zip_file.name}
    """)

    return json_file, zip_file, file_hash

if __name__ == "__main__":
    try:
        create_full_backup()
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()