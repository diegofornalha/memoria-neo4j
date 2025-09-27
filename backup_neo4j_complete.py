#!/usr/bin/env python3
"""
Script para fazer backup completo de todos os aprendizados do Neo4j
Com paginação para evitar estouro de memória
"""

import json
import os
from datetime import datetime
from pathlib import Path
from neo4j import GraphDatabase
import sys

def create_backup():
    """Cria backup completo do Neo4j com paginação"""

    # Conectar ao Neo4j
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "00")
    )

    print("🔗 Conectado ao Neo4j")

    # Criar diretório de backup
    backup_dir = Path("/Users/2a/.claude/memoria-neo4j-claude-code-sdk/backups")
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"neo4j_backup_{timestamp}.json"

    backup_data = {
        "metadata": {
            "timestamp": timestamp,
            "date": datetime.now().isoformat(),
            "stats": {}
        },
        "nodes": [],
        "relationships": []
    }

    try:
        # 1. Buscar estatísticas
        stats_query = """
        MATCH (n)
        WITH labels(n) as labels, count(n) as count
        UNWIND labels as label
        RETURN label, sum(count) as total
        ORDER BY total DESC
        """

        with driver.session() as session:
            stats_result = session.run(stats_query)
            label_stats = {r['label']: r['total'] for r in stats_result}
        backup_data['metadata']['stats'] = label_stats

        print(f"📊 Estatísticas coletadas: {len(label_stats)} labels encontrados")

        # 2. Exportar nós por label com paginação
        for label, count in label_stats.items():
            print(f"📦 Exportando {count} nós do tipo '{label}'...")

            # Buscar nós em lotes de 50
            offset = 0
            batch_size = 50

            while offset < count:
                nodes_query = f"""
                MATCH (n:{label})
                WITH n, id(n) as node_id
                RETURN node_id, labels(n) as labels, properties(n) as props
                ORDER BY node_id
                SKIP {offset}
                LIMIT {batch_size}
                """

                with driver.session() as session:
                    batch_result = list(session.run(nodes_query))

                for node in batch_result:
                    backup_data['nodes'].append({
                        'id': node['node_id'],
                        'labels': node['labels'],
                        'properties': node['props']
                    })

                offset += batch_size
                if offset < count:
                    print(f"   ↳ Processados {min(offset, count)}/{count} nós...")

        print(f"✅ Total de {len(backup_data['nodes'])} nós exportados")

        # 3. Exportar relacionamentos com paginação
        print("🔗 Exportando relacionamentos...")

        rel_count_query = """
        MATCH ()-[r]->()
        RETURN count(r) as total
        """
        with driver.session() as session:
            rel_count_result = list(session.run(rel_count_query))
        total_rels = rel_count_result[0]['total'] if rel_count_result else 0

        offset = 0
        batch_size = 100

        while offset < total_rels:
            rels_query = f"""
            MATCH (a)-[r]->(b)
            WITH a, r, b, id(a) as start_id, id(b) as end_id, id(r) as rel_id
            RETURN start_id, end_id, rel_id, type(r) as type, properties(r) as props
            ORDER BY rel_id
            SKIP {offset}
            LIMIT {batch_size}
            """

            with driver.session() as session:
                batch_result = list(session.run(rels_query))

            for rel in batch_result:
                backup_data['relationships'].append({
                    'id': rel['rel_id'],
                    'start': rel['start_id'],
                    'end': rel['end_id'],
                    'type': rel['type'],
                    'properties': rel['props']
                })

            offset += batch_size
            if offset < total_rels:
                print(f"   ↳ Processados {min(offset, total_rels)}/{total_rels} relacionamentos...")

        print(f"✅ Total de {len(backup_data['relationships'])} relacionamentos exportados")

        # 4. Salvar backup
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)

        file_size = backup_file.stat().st_size / (1024 * 1024)  # MB

        print(f"\n📁 Backup salvo em: {backup_file}")
        print(f"📏 Tamanho: {file_size:.2f} MB")
        print(f"📊 Resumo:")
        print(f"   • Nós: {len(backup_data['nodes'])}")
        print(f"   • Relacionamentos: {len(backup_data['relationships'])}")
        print(f"   • Labels: {len(label_stats)}")

        # 5. Criar arquivo de resumo
        summary_file = backup_dir / f"backup_summary_{timestamp}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"Neo4j Backup Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")

            f.write("📊 Estatísticas por Label:\n")
            f.write("-"*30 + "\n")
            for label, count in sorted(label_stats.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{label:30} {count:5} nós\n")

            f.write(f"\n{'Total':30} {sum(label_stats.values()):5} nós\n")
            f.write(f"{'Relacionamentos':30} {len(backup_data['relationships']):5}\n")

        print(f"📄 Resumo salvo em: {summary_file}")

        return backup_file

    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        raise
    finally:
        driver.close()

if __name__ == "__main__":
    try:
        backup_file = create_backup()
        print(f"\n✅ Backup completo realizado com sucesso!")
    except Exception as e:
        print(f"\n❌ Falha no backup: {e}")
        sys.exit(1)