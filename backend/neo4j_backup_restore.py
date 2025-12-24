#!/usr/bin/env python3
"""
Sistema completo de backup e restauracao para Neo4j
Com suporte a dados estruturados e restauracao integral
Versao 3.1 - Com correcoes de seguranca e performance
"""
import json
import hashlib
import zipfile
import tempfile
import shutil
import re
import signal
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

# Logger do modulo (sem basicConfig global)
logger = logging.getLogger(__name__)


class Neo4jConnectionError(Exception):
    """Erro de conexao com Neo4j"""
    pass


class Neo4jConfigError(Exception):
    """Erro de configuracao do Neo4j"""
    pass


class BackupValidationError(Exception):
    """Erro de validacao do backup"""
    pass


# Regex para validar labels Cypher (apenas alfanumericos e underscore)
VALID_LABEL_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
VALID_REL_TYPE_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def validate_cypher_label(label: str) -> bool:
    """Valida se um label eh seguro para usar em Cypher"""
    return bool(VALID_LABEL_PATTERN.match(label))


def validate_cypher_rel_type(rel_type: str) -> bool:
    """Valida se um tipo de relacao eh seguro para usar em Cypher"""
    return bool(VALID_REL_TYPE_PATTERN.match(rel_type))


def sanitize_label(label: str) -> str:
    """Sanitiza label removendo caracteres invalidos"""
    # Remove caracteres nao alfanumericos (exceto underscore)
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', label)
    # Garante que comeca com letra ou underscore
    if sanitized and sanitized[0].isdigit():
        sanitized = '_' + sanitized
    return sanitized or 'Node'


def input_with_timeout(prompt: str, timeout: int = 30, default: str = "no") -> str:
    """
    Input com timeout para evitar blocking infinito

    Args:
        prompt: Mensagem para o usuario
        timeout: Tempo maximo em segundos
        default: Valor padrao se timeout
    """
    def timeout_handler(signum, frame):
        raise TimeoutError()

    # Em ambientes nao-interativos, retorna default
    if not sys.stdin.isatty():
        logger.info(f"Ambiente nao-interativo, usando default: {default}")
        return default

    try:
        # Configura handler de timeout (apenas Unix)
        if hasattr(signal, 'SIGALRM'):
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

        try:
            result = input(prompt)
        finally:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        return result

    except TimeoutError:
        print(f"\n⏱️  Timeout ({timeout}s), usando default: {default}")
        return default
    except EOFError:
        return default


class Neo4jBackupRestore:
    def __init__(self, raise_on_error: bool = False):
        """
        Inicializa conexao com Neo4j

        Args:
            raise_on_error: Se True, lanca excecao ao inves de sys.exit()
                           Util para testes e uso como biblioteca
        """
        self.driver = None
        self.raise_on_error = raise_on_error
        self._temp_dirs: List[Path] = []  # Rastrear diretorios temporarios
        self._connect()

    def _handle_error(self, error: Exception, message: str) -> None:
        """Trata erros de forma consistente"""
        logger.error(f"{message}: {error}")
        print(f"❌ {message}: {error}")

        if self.raise_on_error:
            raise error
        else:
            sys.exit(1)

    def _connect(self) -> None:
        """Estabelece conexao com Neo4j usando credenciais do config"""
        try:
            auth = get_neo4j_auth()
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=auth)
            self.verify_connection()
            logger.info("Conexao com Neo4j estabelecida")

        except ValueError as e:
            print("💡 Configure NEO4J_PASSWORD via variavel de ambiente ou arquivo .env")
            self._handle_error(Neo4jConfigError(str(e)), "Erro de configuracao")

        except AuthError as e:
            print("💡 Verifique NEO4J_USERNAME e NEO4J_PASSWORD")
            self._handle_error(Neo4jConnectionError(str(e)), "Erro de autenticacao")

        except ServiceUnavailable as e:
            print(f"💡 Verifique se o Neo4j esta rodando em {NEO4J_URI}")
            self._handle_error(Neo4jConnectionError(str(e)), "Neo4j nao disponivel")

        except Exception as e:
            self._handle_error(Neo4jConnectionError(str(e)), "Erro ao conectar")

    def verify_connection(self) -> None:
        """Verifica se a conexao esta ativa"""
        with self.driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record is None:
                raise Neo4jConnectionError("Conexao retornou resultado vazio")

    def close(self) -> None:
        """Fecha conexao e limpa recursos temporarios"""
        if self.driver:
            self.driver.close()
            logger.info("Conexao Neo4j fechada")

        # Limpar diretorios temporarios
        for temp_dir in self._temp_dirs:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Diretorio temporario removido: {temp_dir}")
            except Exception as e:
                logger.warning(f"Erro ao remover {temp_dir}: {e}")

        self._temp_dirs.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def create_backup(self, tag: Optional[str] = None) -> Optional[Tuple[Path, Path]]:
        """Cria backup completo do Neo4j"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        print("🔒 Neo4j Backup Completo v3.1")
        print("=" * 50)

        try:
            with self.driver.session() as session:
                # 1. Contar dados
                print("📊 Analisando banco de dados...")

                node_result = session.run("MATCH (n) RETURN count(n) as count").single()
                rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()

                node_count = node_result["count"] if node_result else 0
                rel_count = rel_result["count"] if rel_result else 0

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
                "version": "3.1",
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

        # Evitar divisao por zero
        if file_size > 0:
            compression = (1 - zip_size / file_size) * 100
        else:
            compression = 0

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

        # 1. Extrair se for ZIP (com validacao de seguranca)
        json_file = self._extract_backup_safe(backup_path)
        if json_file is None:
            return False

        # 2. Carregar e validar backup
        print("📂 Carregando backup...")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Arquivo JSON invalido: {e}")
            return False

        # 3. Validar schema do backup
        if not self._validate_backup_schema(backup_data):
            return False

        metadata = backup_data.get("metadata", {})
        nodes = backup_data.get("nodes", [])
        relations = backup_data.get("relations", [])

        print(f"  - Data do backup: {metadata.get('date', 'Desconhecida')}")
        print(f"  - Nos a restaurar: {len(nodes):,}")
        print(f"  - Relacoes a restaurar: {len(relations):,}")

        # 4. Verificar e limpar banco
        if not self._prepare_database_for_restore():
            return False

        # 5. Restaurar dados usando batch otimizado
        try:
            with self.driver.session() as session:
                id_mapping = self._restore_nodes_batch(session, nodes)
                restored_rels = self._restore_relations_batch(session, relations, id_mapping)

                # 6. Verificar resultado
                self._verify_restore(session)

        except Exception as e:
            logger.error(f"Erro durante restauracao: {e}")
            print(f"❌ Erro durante restauracao: {e}")
            return False

        print("\n" + "=" * 50)
        print("✅ RESTAURACAO COMPLETA COM SUCESSO!")

        return True

    def _extract_backup_safe(self, backup_path: Path) -> Optional[Path]:
        """
        Extrai backup de forma segura (previne path traversal)
        """
        if backup_path.suffix != '.zip':
            return backup_path

        print("📦 Extraindo arquivo ZIP...")

        # Usar tempfile seguro ao inves de /tmp global
        temp_dir = Path(tempfile.mkdtemp(prefix="neo4j_restore_"))
        self._temp_dirs.append(temp_dir)  # Rastrear para limpeza

        try:
            with zipfile.ZipFile(backup_path, 'r') as zf:
                # Validar cada arquivo antes de extrair (previne path traversal)
                for member in zf.namelist():
                    # Verificar se o caminho eh seguro
                    member_path = Path(member)

                    # Rejeitar caminhos absolutos
                    if member_path.is_absolute():
                        logger.warning(f"Caminho absoluto rejeitado: {member}")
                        continue

                    # Rejeitar path traversal (../)
                    try:
                        # Resolve o caminho e verifica se esta dentro de temp_dir
                        target_path = (temp_dir / member).resolve()
                        if not str(target_path).startswith(str(temp_dir.resolve())):
                            logger.warning(f"Path traversal detectado: {member}")
                            continue
                    except (ValueError, RuntimeError):
                        logger.warning(f"Caminho invalido: {member}")
                        continue

                    # Extrair apenas arquivos JSON seguros
                    if member.endswith('.json'):
                        zf.extract(member, temp_dir)
                        logger.debug(f"Extraido: {member}")

            json_files = list(temp_dir.glob("*.json"))
            if not json_files:
                print("❌ Arquivo JSON nao encontrado no ZIP")
                return None

            return json_files[0]

        except zipfile.BadZipFile as e:
            print(f"❌ Arquivo ZIP corrompido: {e}")
            return None

    def _validate_backup_schema(self, backup_data: Dict) -> bool:
        """Valida schema do arquivo de backup"""
        required_keys = ["metadata", "nodes", "relations"]

        for key in required_keys:
            if key not in backup_data:
                print(f"❌ Backup invalido: falta chave '{key}'")
                return False

        metadata = backup_data["metadata"]
        if not isinstance(metadata, dict):
            print("❌ Backup invalido: metadata deve ser um objeto")
            return False

        nodes = backup_data["nodes"]
        if not isinstance(nodes, list):
            print("❌ Backup invalido: nodes deve ser uma lista")
            return False

        relations = backup_data["relations"]
        if not isinstance(relations, list):
            print("❌ Backup invalido: relations deve ser uma lista")
            return False

        # Validar estrutura dos nos (amostra)
        if nodes:
            sample_node = nodes[0]
            if not isinstance(sample_node, dict):
                print("❌ Backup invalido: cada node deve ser um objeto")
                return False
            if "labels" not in sample_node and "properties" not in sample_node:
                print("❌ Backup invalido: nodes devem ter 'labels' ou 'properties'")
                return False

        print("  ✅ Schema do backup validado")
        return True

    def _prepare_database_for_restore(self) -> bool:
        """Prepara banco para restauracao (verifica e limpa se necessario)"""
        try:
            with self.driver.session() as session:
                node_result = session.run("MATCH (n) RETURN count(n) as count").single()
                rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()

                current_nodes = node_result["count"] if node_result else 0
                current_rels = rel_result["count"] if rel_result else 0

                print(f"\n📊 Estado atual:")
                print(f"  - Nos existentes: {current_nodes:,}")
                print(f"  - Relacoes existentes: {current_rels:,}")

                if current_nodes > 0 or current_rels > 0:
                    print("\n⚠️  ATENCAO: O banco nao esta vazio!")
                    confirm = input_with_timeout(
                        "  Limpar banco antes de restaurar? (yes/no): ",
                        timeout=60,
                        default="no"
                    )

                    if confirm.lower() == 'yes':
                        print("\n🗑️  Limpando banco...")
                        # Usar transacao atomica
                        with session.begin_transaction() as tx:
                            tx.run("MATCH ()-[r]->() DELETE r")
                            tx.run("MATCH (n) DELETE n")
                            tx.commit()
                        print("  ✅ Banco limpo")

                return True

        except Exception as e:
            logger.error(f"Erro preparando banco: {e}")
            print(f"❌ Erro preparando banco: {e}")
            return False

    def _restore_nodes_batch(self, session, nodes: List[Dict]) -> Dict[int, int]:
        """
        Restaura nos usando UNWIND batch otimizado

        Returns:
            Mapeamento de IDs antigos para novos
        """
        print("\n📥 Restaurando nos...")
        id_mapping = {}
        batch_size = 500  # Maior batch para melhor performance

        # Agrupar nos por labels para batch mais eficiente
        nodes_by_labels: Dict[str, List[Dict]] = {}

        for node in nodes:
            raw_labels = node.get("labels", [])
            # Validar e sanitizar labels
            safe_labels = []
            for label in raw_labels:
                if validate_cypher_label(label):
                    safe_labels.append(label)
                else:
                    sanitized = sanitize_label(label)
                    safe_labels.append(sanitized)
                    logger.warning(f"Label sanitizado: {label} -> {sanitized}")

            labels_key = ":".join(sorted(safe_labels)) if safe_labels else "Node"
            if labels_key not in nodes_by_labels:
                nodes_by_labels[labels_key] = []
            nodes_by_labels[labels_key].append({
                "old_id": node.get("id"),
                "props": node.get("properties", {})
            })

        total_processed = 0
        total_nodes = len(nodes)

        for labels_str, label_nodes in nodes_by_labels.items():
            # Processar em batches
            for i in range(0, len(label_nodes), batch_size):
                batch = label_nodes[i:i + batch_size]
                batch_data = [{"props": n["props"]} for n in batch]
                batch_old_ids = [n["old_id"] for n in batch]

                # Query batch com UNWIND (muito mais rapido)
                query = f"""
                UNWIND $batch as item
                CREATE (n:{labels_str})
                SET n = item.props
                RETURN id(n) as new_id
                """

                try:
                    result = session.run(query, batch=batch_data)
                    new_ids = [record["new_id"] for record in result]

                    # Mapear IDs
                    for old_id, new_id in zip(batch_old_ids, new_ids):
                        if old_id is not None:
                            id_mapping[old_id] = new_id

                except Exception as e:
                    logger.warning(f"Erro no batch de nos ({labels_str}): {e}")
                    # Fallback para criacao individual
                    for node_data, old_id in zip(batch, batch_old_ids):
                        try:
                            result = session.run(
                                f"CREATE (n:{labels_str} $props) RETURN id(n) as new_id",
                                props=node_data["props"]
                            )
                            record = result.single()
                            if record and old_id is not None:
                                id_mapping[old_id] = record["new_id"]
                        except Exception as e2:
                            logger.warning(f"Erro ao criar no {old_id}: {e2}")

                total_processed += len(batch)
                percent = (total_processed / total_nodes) * 100
                print(f"  [{total_processed}/{total_nodes}] {percent:.1f}%", end='\r')

        print(f"\n  ✅ {len(id_mapping)} nos restaurados")
        return id_mapping

    def _restore_relations_batch(
        self,
        session,
        relations: List[Dict],
        id_mapping: Dict[int, int]
    ) -> int:
        """
        Restaura relacoes usando UNWIND batch otimizado
        """
        print("\n📥 Restaurando relacoes...")
        restored_rels = 0
        batch_size = 500

        # Agrupar por tipo de relacao
        rels_by_type: Dict[str, List[Dict]] = {}

        for rel in relations:
            source_old = rel.get("source")
            target_old = rel.get("target")

            if source_old not in id_mapping or target_old not in id_mapping:
                continue

            raw_type = rel.get("type", "RELATED_TO")

            # Validar tipo de relacao
            if validate_cypher_rel_type(raw_type):
                rel_type = raw_type
            else:
                rel_type = sanitize_label(raw_type)
                logger.warning(f"Tipo de relacao sanitizado: {raw_type} -> {rel_type}")

            if rel_type not in rels_by_type:
                rels_by_type[rel_type] = []

            rels_by_type[rel_type].append({
                "source_id": id_mapping[source_old],
                "target_id": id_mapping[target_old],
                "props": rel.get("properties", {})
            })

        total_rels = sum(len(r) for r in rels_by_type.values())
        total_processed = 0

        for rel_type, type_rels in rels_by_type.items():
            for i in range(0, len(type_rels), batch_size):
                batch = type_rels[i:i + batch_size]

                # Query batch com UNWIND
                query = f"""
                UNWIND $batch as item
                MATCH (a) WHERE id(a) = item.source_id
                MATCH (b) WHERE id(b) = item.target_id
                CREATE (a)-[r:{rel_type}]->(b)
                SET r = item.props
                RETURN count(r) as created
                """

                try:
                    result = session.run(query, batch=batch)
                    record = result.single()
                    if record:
                        restored_rels += record["created"]
                except Exception as e:
                    logger.warning(f"Erro no batch de relacoes ({rel_type}): {e}")
                    # Fallback individual
                    for rel_data in batch:
                        try:
                            session.run(
                                f"""
                                MATCH (a) WHERE id(a) = $source_id
                                MATCH (b) WHERE id(b) = $target_id
                                CREATE (a)-[r:{rel_type} $props]->(b)
                                """,
                                source_id=rel_data["source_id"],
                                target_id=rel_data["target_id"],
                                props=rel_data["props"]
                            )
                            restored_rels += 1
                        except Exception as e2:
                            logger.warning(f"Erro ao criar relacao: {e2}")

                total_processed += len(batch)
                if total_rels > 0:
                    percent = (total_processed / total_rels) * 100
                    print(f"  [{total_processed}/{total_rels}] {percent:.1f}%", end='\r')

        print(f"\n  ✅ {restored_rels} relacoes restauradas")
        return restored_rels

    def _verify_restore(self, session) -> None:
        """Verifica resultado da restauracao"""
        print("\n🔍 Verificando restauracao...")

        node_result = session.run("MATCH (n) RETURN count(n) as count").single()
        rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()

        final_nodes = node_result["count"] if node_result else 0
        final_rels = rel_result["count"] if rel_result else 0

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
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Log corrompido, criando novo")

        log_data.append(entry)

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)


def main():
    """Funcao principal"""
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python3 neo4j_backup_restore.py backup [tag]")
        print("  python3 neo4j_backup_restore.py restore <arquivo>")
        return

    command = sys.argv[1]

    # Usar context manager para garantir limpeza
    with Neo4jBackupRestore() as neo4j:
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


if __name__ == "__main__":
    main()
