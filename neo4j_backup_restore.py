#!/usr/bin/env python3
"""
Sistema completo de backup e restauração para Neo4j
Com suporte a dados estruturados e restauração integral
"""
import json
import hashlib
import zipfile
from datetime import datetime
from pathlib import Path
import sys
import os
from neo4j import GraphDatabase
import time

# Configurações do Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Diretórios
BACKUP_DIR = Path("/Users/2a/.claude/memoria-neo4j/backups")
BACKUP_DIR.mkdir(exist_ok=True)

class Neo4jBackupRestore:
    def __init__(self):
        """Inicializa conexão com Neo4j"""
        try:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            self.verify_connection()
        except Exception as e:
            print(f"⚠️ Erro conectando ao Neo4j: {e}")
            print("Tentando credenciais alternativas...")

            # Tentar sem senha
            try:
                self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, ""))
                self.verify_connection()
            except:
                # Tentar com senha padrão
                try:
                    self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, "neo4j"))
                    self.verify_connection()
                except Exception as e:
                    print(f"❌ Não foi possível conectar ao Neo4j: {e}")
                    sys.exit(1)

    def verify_connection(self):
        """Verifica se a conexão está ativa"""
        with self.driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()

    def close(self):
        """Fecha conexão"""
        if self.driver:
            self.driver.close()

    def create_backup(self, tag=None):
        """Cria backup completo do Neo4j"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        print("🔒 Neo4j Backup Completo v2.0")
        print("=" * 50)

        try:
            with self.driver.session() as session:
                # 1. Contar dados
                print("📊 Analisando banco de dados...")

                node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

                print(f"  • Total de nós: {node_count:,}")
                print(f"  • Total de relações: {rel_count:,}")

                # 2. Exportar nós
                print("\n📤 Exportando nós...")

                nodes_data = []
                result = session.run("""
                    MATCH (n)
                    RETURN id(n) as id,
                           labels(n) as labels,
                           properties(n) as props
                """)

                for record in result:
                    node = {
                        "id": record["id"],
                        "labels": list(record["labels"]),
                        "properties": dict(record["props"]) if record["props"] else {}
                    }
                    nodes_data.append(node)

                print(f"  ✅ {len(nodes_data)} nós exportados")

                # 3. Exportar relações
                print("📤 Exportando relações...")

                relations_data = []
                result = session.run("""
                    MATCH (a)-[r]->(b)
                    RETURN id(a) as source,
                           id(b) as target,
                           type(r) as type,
                           properties(r) as props
                """)

                for record in result:
                    relation = {
                        "source": record["source"],
                        "target": record["target"],
                        "type": record["type"],
                        "properties": dict(record["props"]) if record["props"] else {}
                    }
                    relations_data.append(relation)

                print(f"  ✅ {len(relations_data)} relações exportadas")

                # 4. Estatísticas por label
                print("\n📊 Analisando labels...")

                label_stats = {}
                result = session.run("""
                    MATCH (n)
                    UNWIND labels(n) as label
                    RETURN label, count(n) as count
                    ORDER BY count DESC
                """)

                for record in result:
                    label_stats[record["label"]] = record["count"]

                print(f"  • Labels encontrados: {len(label_stats)}")
                for label, count in list(label_stats.items())[:5]:
                    print(f"    - {label}: {count}")

        except Exception as e:
            print(f"❌ Erro ao exportar dados: {e}")
            return None

        # 5. Criar estrutura do backup
        backup_data = {
            "metadata": {
                "version": "2.0",
                "timestamp": timestamp,
                "date": datetime.now().isoformat(),
                "tag": tag,
                "neo4j_uri": NEO4J_URI,
                "statistics": {
                    "total_nodes": len(nodes_data),
                    "total_relations": len(relations_data),
                    "labels": label_stats
                }
            },
            "nodes": nodes_data,
            "relations": relations_data
        }

        # 6. Salvar JSON
        json_file = BACKUP_DIR / f"BACKUP_COMPLETE_{timestamp}.json"
        if tag:
            json_file = BACKUP_DIR / f"BACKUP_COMPLETE_{timestamp}_{tag}.json"

        print(f"\n💾 Salvando backup...")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        file_size = json_file.stat().st_size
        print(f"  ✅ Arquivo: {json_file.name}")
        print(f"  📊 Tamanho: {file_size / 1024 / 1024:.2f} MB")

        # 7. Gerar hash
        print("\n🔐 Gerando hash SHA256...")
        with open(json_file, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        hash_file = json_file.with_suffix('.sha256')
        with open(hash_file, 'w') as f:
            f.write(f"{file_hash}  {json_file.name}\n")

        print(f"  ✅ Hash: {file_hash[:32]}...")

        # 8. Criar ZIP
        print("\n📦 Comprimindo backup...")
        zip_file = json_file.with_suffix('.zip')

        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(json_file, json_file.name)
            zf.write(hash_file, hash_file.name)

        zip_size = zip_file.stat().st_size
        compression = (1 - zip_size / file_size) * 100

        print(f"  ✅ ZIP: {zip_file.name}")
        print(f"  📊 Compressão: {compression:.1f}%")
        print(f"  💾 Tamanho final: {zip_size / 1024 / 1024:.2f} MB")

        # 9. Atualizar log
        self.update_log(json_file, zip_file, file_hash, nodes_data, relations_data, tag)

        print("\n" + "=" * 50)
        print("✅ BACKUP COMPLETO CRIADO COM SUCESSO!")

        return json_file, zip_file

    def restore_backup(self, backup_file):
        """Restaura backup completo do Neo4j"""

        backup_path = Path(backup_file)

        if not backup_path.exists():
            print(f"❌ Arquivo não encontrado: {backup_file}")
            return False

        print("🔄 Restauração Completa do Neo4j")
        print("=" * 50)

        # 1. Extrair se for ZIP
        if backup_path.suffix == '.zip':
            print("📦 Extraindo arquivo ZIP...")
            temp_dir = Path("/tmp/neo4j_restore")
            temp_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(backup_path, 'r') as zf:
                zf.extractall(temp_dir)

            json_files = list(temp_dir.glob("*.json"))
            if not json_files:
                print("❌ Arquivo JSON não encontrado no ZIP")
                return False

            json_file = json_files[0]
        else:
            json_file = backup_path

        # 2. Carregar backup
        print("📂 Carregando backup...")
        with open(json_file, 'r') as f:
            backup_data = json.load(f)

        metadata = backup_data.get("metadata", {})
        nodes = backup_data.get("nodes", [])
        relations = backup_data.get("relations", [])

        print(f"  • Data do backup: {metadata.get('date', 'Desconhecida')}")
        print(f"  • Nós a restaurar: {len(nodes):,}")
        print(f"  • Relações a restaurar: {len(relations):,}")

        # 3. Verificar estado atual
        try:
            with self.driver.session() as session:
                current_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
                current_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

                print(f"\n📊 Estado atual:")
                print(f"  • Nós existentes: {current_nodes:,}")
                print(f"  • Relações existentes: {current_rels:,}")

                if current_nodes > 0 or current_rels > 0:
                    print("\n⚠️  ATENÇÃO: O banco não está vazio!")
                    confirm = input("  Limpar banco antes de restaurar? (yes/no): ")

                    if confirm.lower() == 'yes':
                        print("\n🗑️  Limpando banco...")

                        # Deletar relações primeiro
                        session.run("MATCH ()-[r]->() DELETE r")
                        print("  ✅ Relações removidas")

                        # Deletar nós
                        session.run("MATCH (n) DELETE n")
                        print("  ✅ Nós removidos")

                # 4. Restaurar nós
                print("\n📥 Restaurando nós...")

                # Criar mapeamento de IDs antigos para novos
                id_mapping = {}
                batch_size = 100

                for i in range(0, len(nodes), batch_size):
                    batch = nodes[i:i+batch_size]

                    for node in batch:
                        # Criar query para cada nó
                        labels = ":".join(node["labels"]) if node["labels"] else ""

                        # Preparar propriedades
                        props_str = ""
                        if node["properties"]:
                            props = []
                            for key, value in node["properties"].items():
                                if isinstance(value, str):
                                    value = value.replace("'", "\\'")
                                    props.append(f"{key}: '{value}'")
                                elif value is not None:
                                    props.append(f"{key}: {json.dumps(value)}")
                            props_str = "{" + ", ".join(props) + "}"
                        else:
                            props_str = "{}"

                        # Criar nó e capturar novo ID
                        if labels:
                            query = f"CREATE (n:{labels} {props_str}) RETURN id(n) as new_id"
                        else:
                            query = f"CREATE (n {props_str}) RETURN id(n) as new_id"

                        try:
                            result = session.run(query)
                            new_id = result.single()["new_id"]
                            id_mapping[node["id"]] = new_id
                        except Exception as e:
                            print(f"  ⚠️ Erro ao criar nó {node['id']}: {e}")

                    # Progresso
                    progress = min(i + batch_size, len(nodes))
                    percent = (progress / len(nodes)) * 100
                    print(f"  [{progress}/{len(nodes)}] {percent:.1f}%", end='\r')

                print(f"\n  ✅ {len(id_mapping)} nós restaurados")

                # 5. Restaurar relações
                print("\n📥 Restaurando relações...")

                restored_rels = 0
                for i in range(0, len(relations), batch_size):
                    batch = relations[i:i+batch_size]

                    for rel in batch:
                        # Verificar se os nós existem no mapeamento
                        if rel["source"] not in id_mapping or rel["target"] not in id_mapping:
                            continue

                        source_id = id_mapping[rel["source"]]
                        target_id = id_mapping[rel["target"]]

                        # Preparar propriedades
                        props_str = ""
                        if rel["properties"]:
                            props = []
                            for key, value in rel["properties"].items():
                                if isinstance(value, str):
                                    value = value.replace("'", "\\'")
                                    props.append(f"{key}: '{value}'")
                                elif value is not None:
                                    props.append(f"{key}: {json.dumps(value)}")
                            props_str = "{" + ", ".join(props) + "}"
                        else:
                            props_str = "{}"

                        # Criar relação
                        query = f"""
                        MATCH (a) WHERE id(a) = {source_id}
                        MATCH (b) WHERE id(b) = {target_id}
                        CREATE (a)-[r:{rel["type"]} {props_str}]->(b)
                        """

                        try:
                            session.run(query)
                            restored_rels += 1
                        except Exception as e:
                            print(f"  ⚠️ Erro ao criar relação: {e}")

                    # Progresso
                    progress = min(i + batch_size, len(relations))
                    percent = (progress / len(relations)) * 100
                    print(f"  [{progress}/{len(relations)}] {percent:.1f}%", end='\r')

                print(f"\n  ✅ {restored_rels} relações restauradas")

                # 6. Verificar resultado
                print("\n🔍 Verificando restauração...")

                final_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
                final_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

                print(f"  • Nós finais: {final_nodes:,}")
                print(f"  • Relações finais: {final_rels:,}")

                # Verificar labels
                result = session.run("""
                    MATCH (n)
                    UNWIND labels(n) as label
                    RETURN label, count(n) as count
                    ORDER BY count DESC
                    LIMIT 5
                """)

                print("\n  Top labels restaurados:")
                for record in result:
                    print(f"    - {record['label']}: {record['count']}")

        except Exception as e:
            print(f"❌ Erro durante restauração: {e}")
            return False

        print("\n" + "=" * 50)
        print("✅ RESTAURAÇÃO COMPLETA COM SUCESSO!")

        return True

    def update_log(self, json_file, zip_file, file_hash, nodes, relations, tag):
        """Atualiza log de backups"""
        log_file = BACKUP_DIR / "BACKUP_LOG.json"

        entry = {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "date": datetime.now().isoformat(),
            "json_file": json_file.name,
            "zip_file": zip_file.name,
            "hash": file_hash,
            "size_bytes": json_file.stat().st_size,
            "compressed_bytes": zip_file.stat().st_size,
            "nodes": len(nodes),
            "relations": len(relations),
            "tag": tag
        }

        if log_file.exists():
            with open(log_file, 'r') as f:
                log_data = json.load(f)
        else:
            log_data = []

        log_data.append(entry)

        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)

def main():
    """Função principal"""

    if len(sys.argv) < 2:
        print("Uso:")
        print("  python3 neo4j_backup_restore.py backup [tag]")
        print("  python3 neo4j_backup_restore.py restore <arquivo>")
        return

    command = sys.argv[1]
    neo4j = Neo4jBackupRestore()

    try:
        if command == "backup":
            tag = sys.argv[2] if len(sys.argv) > 2 else None
            neo4j.create_backup(tag)

        elif command == "restore":
            if len(sys.argv) < 3:
                print("❌ Especifique o arquivo de backup")
                return

            backup_file = sys.argv[2]

            # Se for apenas o nome, procurar no diretório de backups
            if not Path(backup_file).exists():
                backup_file = BACKUP_DIR / backup_file

            neo4j.restore_backup(backup_file)

        else:
            print(f"❌ Comando desconhecido: {command}")

    finally:
        neo4j.close()

if __name__ == "__main__":
    main()