#!/usr/bin/env python3
"""
Script para exportar TODOS os dados do Neo4j diretamente
Conecta ao Neo4j e faz queries paginadas para exportar tudo
"""

import json
from datetime import datetime
from neo4j import GraphDatabase
from neo4j.time import DateTime
import os

def convert_neo4j_types(obj):
    """Converte tipos do Neo4j para tipos serializáveis em JSON"""
    if isinstance(obj, DateTime):
        return obj.iso_format()
    elif isinstance(obj, dict):
        return {k: convert_neo4j_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_neo4j_types(item) for item in obj]
    return obj

# Configuração do Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

def export_all_nodes(driver, batch_size=100):
    """Exporta todos os nós do Neo4j em lotes"""

    all_nodes = []
    skip = 0

    with driver.session() as session:
        while True:
            print(f"📥 Buscando nós {skip} a {skip + batch_size}...")

            # Query para buscar nós com todos os relacionamentos
            result = session.run("""
                MATCH (n)
                OPTIONAL MATCH (n)-[r]->(m)
                RETURN n,
                       labels(n) as labels,
                       properties(n) as props,
                       collect({
                           type: type(r),
                           target_id: id(m),
                           target_labels: labels(m),
                           properties: properties(r)
                       }) as relationships
                ORDER BY id(n)
                SKIP $skip
                LIMIT $limit
            """, skip=skip, limit=batch_size)

            nodes_in_batch = []
            for record in result:
                node_data = {
                    "id": record["n"].id,
                    "labels": record["labels"],
                    "properties": convert_neo4j_types(dict(record["props"])),
                    "relationships": [
                        convert_neo4j_types(rel) for rel in record["relationships"]
                        if rel["type"] is not None
                    ]
                }
                nodes_in_batch.append(node_data)

            if not nodes_in_batch:
                print("✅ Todos os nós exportados!")
                break

            all_nodes.extend(nodes_in_batch)
            print(f"   ✓ {len(nodes_in_batch)} nós capturados (total: {len(all_nodes)})")
            skip += batch_size

    return all_nodes

def get_statistics(driver):
    """Obtém estatísticas do banco"""
    with driver.session() as session:
        # Total de nós
        result = session.run("MATCH (n) RETURN count(n) as total")
        total_nodes = result.single()["total"]

        # Total de relacionamentos
        result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
        total_rels = result.single()["total"]

        # Labels e suas contagens
        result = session.run("""
            MATCH (n)
            UNWIND labels(n) as label
            RETURN label, count(*) as count
            ORDER BY count DESC
        """)
        labels_stats = [{"label": record["label"], "count": record["count"]}
                       for record in result]

        return {
            "total_nodes": total_nodes,
            "total_relationships": total_rels,
            "labels": labels_stats
        }

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"/Users/2a/.claude/memoria-neo4j-claude-code-sdk/backups/neo4j_backup_{timestamp}.json"

    print("🚀 Iniciando exportação completa do Neo4j...")
    print(f"📍 Conectando em: {NEO4J_URI}")

    # Conecta ao Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        # Verifica conexão
        driver.verify_connectivity()
        print("✅ Conexão estabelecida com sucesso!\n")

        # Obtém estatísticas
        print("📊 Coletando estatísticas...")
        stats = get_statistics(driver)
        print(f"   Total de nós: {stats['total_nodes']}")
        print(f"   Total de relacionamentos: {stats['total_relationships']}")
        print(f"   Labels únicos: {len(stats['labels'])}\n")

        # Exporta todos os nós
        print("📦 Exportando todos os nós...")
        all_nodes = export_all_nodes(driver, batch_size=100)

        # Monta estrutura final
        backup_data = {
            "export_timestamp": datetime.now().isoformat(),
            "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "statistics": stats,
            "nodes": all_nodes,
            "metadata": {
                "neo4j_uri": NEO4J_URI,
                "total_exported": len(all_nodes),
                "export_method": "direct_neo4j_connection"
            }
        }

        # Salva arquivo
        print(f"\n💾 Salvando backup em: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)

        # Estatísticas finais
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
        print(f"\n✅ Backup concluído com sucesso!")
        print(f"📁 Arquivo: {output_file}")
        print(f"📊 Tamanho: {file_size:.2f} MB")
        print(f"📈 Nós exportados: {len(all_nodes)}")
        print(f"🏷️  Labels: {len(stats['labels'])}")
        print(f"🔗 Relacionamentos: {stats['total_relationships']}")

    except Exception as e:
        print(f"\n❌ Erro durante exportação: {e}")
        import traceback
        traceback.print_exc()

    finally:
        driver.close()
        print("\n🔌 Conexão fechada.")

if __name__ == "__main__":
    main()