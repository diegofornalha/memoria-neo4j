#!/usr/bin/env python3
"""
🔒 Neo4j Backup Completo MCP v3.0
Sistema de backup completo com todos os nós e relacionamentos
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from neo4j import GraphDatabase
import hashlib
import zipfile

class Neo4jCompleteBackup:
    def __init__(self):
        # Configurações de conexão
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")

        # Diretórios
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        self.backup_dir = self.project_root / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        self.driver = None

    def connect(self):
        """Conecta ao Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Testar conexão
            with self.driver.session() as session:
                session.run("RETURN 1")
            print(f"✅ Conectado ao Neo4j em {self.uri}")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False

    def get_statistics(self):
        """Obtém estatísticas do banco"""
        with self.driver.session() as session:
            # Contar nós por label
            labels_query = """
            MATCH (n)
            UNWIND labels(n) as label
            RETURN label, count(*) as count
            ORDER BY count DESC
            """
            labels_result = list(session.run(labels_query))

            # Contar relacionamentos
            rels_query = """
            MATCH ()-[r]->()
            RETURN type(r) as type, count(*) as count
            ORDER BY count DESC
            """
            rels_result = list(session.run(rels_query))

            # Total de nós
            total_nodes_query = "MATCH (n) RETURN count(n) as total"
            total_nodes = session.run(total_nodes_query).single()["total"]

            # Total de relacionamentos
            total_rels_query = "MATCH ()-[r]->() RETURN count(r) as total"
            total_rels = session.run(total_rels_query).single()["total"]

            return {
                "total_nodes": total_nodes,
                "total_relationships": total_rels,
                "labels": [{"label": r["label"], "count": r["count"]} for r in labels_result],
                "relationship_types": [{"type": r["type"], "count": r["count"]} for r in rels_result]
            }

    def export_nodes(self):
        """Exporta todos os nós com paginação"""
        all_nodes = []

        with self.driver.session() as session:
            # Primeiro, obter total de nós
            total = session.run("MATCH (n) RETURN count(n) as total").single()["total"]
            print(f"📊 Exportando {total} nós...")

            # Exportar em lotes
            batch_size = 100
            offset = 0

            while offset < total:
                query = f"""
                MATCH (n)
                RETURN
                    id(n) as id,
                    labels(n) as labels,
                    properties(n) as properties
                ORDER BY id(n)
                SKIP {offset}
                LIMIT {batch_size}
                """

                batch = list(session.run(query))

                for record in batch:
                    node_data = {
                        "id": record["id"],
                        "labels": record["labels"],
                        "properties": self._serialize_properties(record["properties"])
                    }
                    all_nodes.append(node_data)

                offset += batch_size
                if offset < total:
                    print(f"   ↳ Processados {min(offset, total)}/{total} nós...")

        return all_nodes

    def export_relationships(self):
        """Exporta todos os relacionamentos com paginação"""
        all_relationships = []

        with self.driver.session() as session:
            # Primeiro, obter total
            total = session.run("MATCH ()-[r]->() RETURN count(r) as total").single()["total"]
            print(f"🔗 Exportando {total} relacionamentos...")

            # Exportar em lotes
            batch_size = 100
            offset = 0

            while offset < total:
                query = f"""
                MATCH (a)-[r]->(b)
                RETURN
                    id(r) as id,
                    id(a) as start_id,
                    id(b) as end_id,
                    type(r) as type,
                    properties(r) as properties
                ORDER BY id(r)
                SKIP {offset}
                LIMIT {batch_size}
                """

                batch = list(session.run(query))

                for record in batch:
                    rel_data = {
                        "id": record["id"],
                        "start_id": record["start_id"],
                        "end_id": record["end_id"],
                        "type": record["type"],
                        "properties": self._serialize_properties(record["properties"])
                    }
                    all_relationships.append(rel_data)

                offset += batch_size
                if offset < total:
                    print(f"   ↳ Processados {min(offset, total)}/{total} relacionamentos...")

        return all_relationships

    def _serialize_properties(self, props):
        """Serializa propriedades para JSON"""
        if not props:
            return {}

        serialized = {}
        for key, value in props.items():
            # Converter tipos Neo4j para tipos JSON
            if hasattr(value, 'iso_format'):  # DateTime
                serialized[key] = value.iso_format()
            elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
                serialized[key] = value
            else:
                serialized[key] = str(value)

        return serialized

    def create_backup(self):
        """Cria backup completo"""
        if not self.connect():
            return None

        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

        print("\n🚀 Iniciando backup completo...")

        # Coletar dados
        stats = self.get_statistics()
        nodes = self.export_nodes()
        relationships = self.export_relationships()

        # Estrutura do backup
        backup_data = {
            "export_timestamp": timestamp.isoformat(),
            "export_date": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "statistics": stats,
            "nodes": nodes,
            "relationships": relationships
        }

        # Salvar JSON
        json_file = self.backup_dir / f"neo4j_backup_{timestamp_str}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        # Calcular hash
        with open(json_file, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # Criar ZIP
        zip_file = self.backup_dir / f"neo4j_backup_{timestamp_str}.zip"
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(json_file, json_file.name)

        # Tamanhos dos arquivos
        json_size = json_file.stat().st_size / (1024 * 1024)  # MB
        zip_size = zip_file.stat().st_size / (1024 * 1024)  # MB

        # Log do backup
        log_file = self.backup_dir / "BACKUP_LOG.json"
        log_data = {"backups": []}
        if log_file.exists():
            with open(log_file, 'r') as f:
                log_data = json.load(f)

        log_data["backups"].append({
            "timestamp": timestamp.isoformat(),
            "file": json_file.name,
            "zip": zip_file.name,
            "hash": file_hash,
            "nodes": len(nodes),
            "relationships": len(relationships),
            "size_mb": round(json_size, 2),
            "zip_size_mb": round(zip_size, 2)
        })

        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)

        # Relatório
        print(f"\n{'='*60}")
        print(f"✅ BACKUP COMPLETO REALIZADO COM SUCESSO!")
        print(f"{'='*60}")
        print(f"📅 Data/Hora: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Arquivo JSON: {json_file.name} ({json_size:.2f} MB)")
        print(f"🗜️  Arquivo ZIP: {zip_file.name} ({zip_size:.2f} MB)")
        print(f"🔒 SHA256: {file_hash[:32]}...")
        print(f"\n📊 Estatísticas do Backup:")
        print(f"   • Nós exportados: {len(nodes):,}")
        print(f"   • Relacionamentos: {len(relationships):,}")
        print(f"   • Labels únicos: {len(stats['labels'])}")
        print(f"   • Tipos de relacionamento: {len(stats['relationship_types'])}")

        print(f"\n🏆 Top 5 Labels:")
        for item in stats['labels'][:5]:
            print(f"   • {item['label']}: {item['count']} nós")

        # Limpar conexão
        self.driver.close()

        return json_file

    def verify_backup(self, backup_file):
        """Verifica integridade do backup"""
        try:
            with open(backup_file, 'r') as f:
                data = json.load(f)

            print(f"✅ Backup válido: {len(data['nodes'])} nós, {len(data['relationships'])} relacionamentos")
            return True
        except Exception as e:
            print(f"❌ Backup inválido: {e}")
            return False


def main():
    backup = Neo4jCompleteBackup()

    try:
        backup_file = backup.create_backup()
        if backup_file:
            print(f"\n🔍 Verificando integridade...")
            backup.verify_backup(backup_file)
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()