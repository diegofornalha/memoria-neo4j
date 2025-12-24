#!/usr/bin/env python3
"""
Sistema completo de backup e restauracao para Neo4j
Com suporte a dados estruturados e restauracao integral
"""
import json
import hashlib
import zipfile
import logging
from datetime import datetime
from pathlib import Path
import sys
import os
from typing import Optional, Tuple, Dict, List, Any

from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

# Importar configuracoes centralizadas
from config import (
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    BACKUP_DIR,
    get_neo4j_auth
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Neo4jBackupRestore:
    def __init__(self):
        """Inicializa conexao com Neo4j"""
        self.driver = None
        self._connect()

    def _connect(self) -> None:
        """Estabelece conexao com Neo4j usando credenciais do config"""
        try:
            auth = get_neo4j_auth()
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=auth)
            self.verify_connection()
            logger.info("Conexao com Neo4j estabelecida")

        except ValueError as e:
            # Credenciais nao configuradas
            logger.error(f"Erro de configuracao: {e}")
            print(f"❌ {e}")
            print("💡 Configure NEO4J_PASSWORD via variavel de ambiente ou arquivo .env")
            sys.exit(1)

        except AuthError as e:
            logger.error(f"Erro de autenticacao Neo4j: {e}")
            print(f"❌ Erro de autenticacao: {e}")
            print("💡 Verifique NEO4J_USERNAME e NEO4J_PASSWORD")
            sys.exit(1)

        except ServiceUnavailable as e:
            logger.error(f"Neo4j nao disponivel: {e}")
            print(f"❌ Neo4j nao disponivel em {NEO4J_URI}")
            print("💡 Verifique se o Neo4j esta rodando")
            sys.exit(1)

        except Exception as e:
            logger.error(f"Erro inesperado ao conectar: {e}")
            print(f"❌ Erro ao conectar: {e}")
            sys.exit(1)

    def verify_connection(self) -> None:
        """Verifica se a conexao esta ativa"""
        with self.driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()

    def close(self) -> None:
        """Fecha conexao"""
        if self.driver:
            self.driver.close()
            logger.info("Conexao Neo4j fechada")

    def create_backup(self, tag: Optional[str] = None) -> Optional[Tuple[Path, Path]]:
        """Cria backup completo do Neo4j"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        print("🔒 Neo4j Backup Completo v3.0")
        print("=" * 50)

        try:
            with self.driver.session() as session:
                # 1. Contar dados
                print("📊 Analisando banco de dados...")

                node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

                print(f"  - Total de nos: {node_count:,}")
                print(f"  - Total de relacoes: {rel_count:,}")

                # 2. Exportar nos
                print("\n📤 Exportando nos...")
                nodes_data = self._export_nodes(session)
                print(f"  ✅ {len(nodes_data)} nos exportados")

                # 3. Exportar relacoes
                print("📤 Exportando relacoes...")
                relations_data = self._export_relations(session)
                print(f"  ✅ {len(relations_data)} relacoes exportadas")

                # 4. Estatisticas por label
                print("\n📊 Analisando labels...")
                label_stats = self._get_label_stats(session)
                print(f"  - Labels encontrados: {len(label_stats)}")
                for label, count in list(label_stats.items())[:5]:
                    print(f"    - {label}: {count}")

        except Exception as e:
            logger.error(f"Erro ao exportar dados: {e}")
            print(f"❌ Erro ao exportar dados: {e}")
            return None

        # 5. Criar estrutura do backup
        backup_data = {
            "metadata": {
                "version": "3.0",
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

        # 6. Salvar arquivos
        json_file, zip_file, file_hash = self._save_backup_files(
            backup_data, timestamp, tag
        )

        # 7. Atualizar log
        self._update_log(json_file, zip_file, file_hash, nodes_data, relations_data, tag)

        print("\n" + "=" * 50)
        print("✅ BACKUP COMPLETO CRIADO COM SUCESSO!")

        return json_file, zip_file

    def _export_nodes(self, session) -> List[Dict[str, Any]]:
        """Exporta todos os nos do banco"""
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

        return nodes_data

    def _export_relations(self, session) -> List[Dict[str, Any]]:
        """Exporta todas as relacoes do banco"""
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

        return relations_data

    def _get_label_stats(self, session) -> Dict[str, int]:
        """Obtem estatisticas por label"""
        label_stats = {}
        result = session.run("""
            MATCH (n)
            UNWIND labels(n) as label
            RETURN label, count(n) as count
            ORDER BY count DESC
        """)

        for record in result:
            label_stats[record["label"]] = record["count"]

        return label_stats

    def _save_backup_files(
        self,
        backup_data: Dict,
        timestamp: str,
        tag: Optional[str]
    ) -> Tuple[Path, Path, str]:
        """Salva arquivos de backup (JSON, hash, ZIP)"""

        # Nome do arquivo
        if tag:
            json_file = BACKUP_DIR / f"BACKUP_COMPLETE_{timestamp}_{tag}.json"
        else:
            json_file = BACKUP_DIR / f"BACKUP_COMPLETE_{timestamp}.json"

        # Salvar JSON
        print(f"\n💾 Salvando backup...")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        file_size = json_file.stat().st_size
        print(f"  ✅ Arquivo: {json_file.name}")
        print(f"  📊 Tamanho: {file_size / 1024 / 1024:.2f} MB")

        # Gerar hash
        print("\n🔐 Gerando hash SHA256...")
        with open(json_file, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        hash_file = json_file.with_suffix('.sha256')
        with open(hash_file, 'w') as f:
            f.write(f"{file_hash}  {json_file.name}\n")

        print(f"  ✅ Hash: {file_hash[:32]}...")

        # Criar ZIP
        print("\n📦 Comprimindo backup...")
        zip_file = json_file.with_suffix('.zip')

        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(json_file, json_file.name)
            zf.write(hash_file, hash_file.name)

        zip_size = zip_file.stat().st_size
        compression = (1 - zip_size / file_size) * 100

        print(f"  ✅ ZIP: {zip_file.name}")
        print(f"  📊 Compressao: {compression:.1f}%")
        print(f"  💾 Tamanho final: {zip_size / 1024 / 1024:.2f} MB")

        return json_file, zip_file, file_hash

    def restore_backup(self, backup_file: str) -> bool:
        """Restaura backup completo do Neo4j"""
        backup_path = Path(backup_file)

        if not backup_path.exists():
            print(f"❌ Arquivo nao encontrado: {backup_file}")
            return False

        print("🔄 Restauracao Completa do Neo4j")
        print("=" * 50)

        # 1. Extrair se for ZIP
        json_file = self._extract_backup(backup_path)
        if json_file is None:
            return False

        # 2. Carregar backup
        print("📂 Carregando backup...")
        with open(json_file, 'r') as f:
            backup_data = json.load(f)

        metadata = backup_data.get("metadata", {})
        nodes = backup_data.get("nodes", [])
        relations = backup_data.get("relations", [])

        print(f"  - Data do backup: {metadata.get('date', 'Desconhecida')}")
        print(f"  - Nos a restaurar: {len(nodes):,}")
        print(f"  - Relacoes a restaurar: {len(relations):,}")

        # 3. Verificar e limpar banco
        if not self._prepare_database_for_restore():
            return False

        # 4. Restaurar dados usando parametros seguros
        try:
            with self.driver.session() as session:
                id_mapping = self._restore_nodes(session, nodes)
                restored_rels = self._restore_relations(session, relations, id_mapping)

                # 5. Verificar resultado
                self._verify_restore(session)

        except Exception as e:
            logger.error(f"Erro durante restauracao: {e}")
            print(f"❌ Erro durante restauracao: {e}")
            return False

        print("\n" + "=" * 50)
        print("✅ RESTAURACAO COMPLETA COM SUCESSO!")

        return True

    def _extract_backup(self, backup_path: Path) -> Optional[Path]:
        """Extrai backup se for ZIP"""
        if backup_path.suffix == '.zip':
            print("📦 Extraindo arquivo ZIP...")
            temp_dir = Path("/tmp/neo4j_restore")
            temp_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(backup_path, 'r') as zf:
                zf.extractall(temp_dir)

            json_files = list(temp_dir.glob("*.json"))
            if not json_files:
                print("❌ Arquivo JSON nao encontrado no ZIP")
                return None

            return json_files[0]

        return backup_path

    def _prepare_database_for_restore(self) -> bool:
        """Prepara banco para restauracao (verifica e limpa se necessario)"""
        try:
            with self.driver.session() as session:
                current_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
                current_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

                print(f"\n📊 Estado atual:")
                print(f"  - Nos existentes: {current_nodes:,}")
                print(f"  - Relacoes existentes: {current_rels:,}")

                if current_nodes > 0 or current_rels > 0:
                    print("\n⚠️  ATENCAO: O banco nao esta vazio!")
                    confirm = input("  Limpar banco antes de restaurar? (yes/no): ")

                    if confirm.lower() == 'yes':
                        print("\n🗑️  Limpando banco...")
                        session.run("MATCH ()-[r]->() DELETE r")
                        print("  ✅ Relacoes removidas")
                        session.run("MATCH (n) DELETE n")
                        print("  ✅ Nos removidos")

                return True

        except Exception as e:
            logger.error(f"Erro preparando banco: {e}")
            print(f"❌ Erro preparando banco: {e}")
            return False

    def _restore_nodes(self, session, nodes: List[Dict]) -> Dict[int, int]:
        """
        Restaura nos usando parametros seguros (evita injection)

        Returns:
            Mapeamento de IDs antigos para novos
        """
        print("\n📥 Restaurando nos...")
        id_mapping = {}
        batch_size = 100

        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]

            for node in batch:
                labels = node.get("labels", [])
                props = node.get("properties", {})

                # Query com parametros (seguro contra injection)
                labels_str = ":".join(labels) if labels else "Node"
                query = f"CREATE (n:{labels_str} $props) RETURN id(n) as new_id"

                try:
                    result = session.run(query, props=props)
                    new_id = result.single()["new_id"]
                    id_mapping[node["id"]] = new_id
                except Exception as e:
                    logger.warning(f"Erro ao criar no {node['id']}: {e}")

            # Progresso
            progress = min(i + batch_size, len(nodes))
            percent = (progress / len(nodes)) * 100
            print(f"  [{progress}/{len(nodes)}] {percent:.1f}%", end='\r')

        print(f"\n  ✅ {len(id_mapping)} nos restaurados")
        return id_mapping

    def _restore_relations(
        self,
        session,
        relations: List[Dict],
        id_mapping: Dict[int, int]
    ) -> int:
        """
        Restaura relacoes usando parametros seguros

        Returns:
            Numero de relacoes restauradas
        """
        print("\n📥 Restaurando relacoes...")
        restored_rels = 0
        batch_size = 100

        for i in range(0, len(relations), batch_size):
            batch = relations[i:i + batch_size]

            for rel in batch:
                source_old = rel.get("source")
                target_old = rel.get("target")

                if source_old not in id_mapping or target_old not in id_mapping:
                    continue

                source_id = id_mapping[source_old]
                target_id = id_mapping[target_old]
                rel_type = rel.get("type", "RELATED_TO")
                props = rel.get("properties", {})

                # Query com parametros (seguro contra injection)
                query = f"""
                MATCH (a) WHERE id(a) = $source_id
                MATCH (b) WHERE id(b) = $target_id
                CREATE (a)-[r:{rel_type} $props]->(b)
                """

                try:
                    session.run(
                        query,
                        source_id=source_id,
                        target_id=target_id,
                        props=props
                    )
                    restored_rels += 1
                except Exception as e:
                    logger.warning(f"Erro ao criar relacao: {e}")

            # Progresso
            progress = min(i + batch_size, len(relations))
            percent = (progress / len(relations)) * 100
            print(f"  [{progress}/{len(relations)}] {percent:.1f}%", end='\r')

        print(f"\n  ✅ {restored_rels} relacoes restauradas")
        return restored_rels

    def _verify_restore(self, session) -> None:
        """Verifica resultado da restauracao"""
        print("\n🔍 Verificando restauracao...")

        final_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
        final_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

        print(f"  - Nos finais: {final_nodes:,}")
        print(f"  - Relacoes finais: {final_rels:,}")

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

    def _update_log(
        self,
        json_file: Path,
        zip_file: Path,
        file_hash: str,
        nodes: List,
        relations: List,
        tag: Optional[str]
    ) -> None:
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

        log_data = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Log corrompido, criando novo")

        log_data.append(entry)

        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)


def main():
    """Funcao principal"""
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

            # Se for apenas o nome, procurar no diretorio de backups
            if not Path(backup_file).exists():
                backup_file = str(BACKUP_DIR / backup_file)

            neo4j.restore_backup(backup_file)

        else:
            print(f"❌ Comando desconhecido: {command}")

    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
