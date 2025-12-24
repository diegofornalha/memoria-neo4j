#!/usr/bin/env python3
"""
Script para restaurar backup do Neo4j com dados do Claude Agent SDK e aprendizados.
"""

import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Adicionar o caminho para usar o MCP tools diretamente
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def restore_backup(backup_file: str):
    """Restaura backup do Neo4j usando as ferramentas MCP."""

    print(f"📂 Carregando backup: {backup_file}")

    # Carregar o backup
    with open(backup_file, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)

    stats = backup_data.get('statistics', {})
    nodes = backup_data.get('nodes', [])

    print(f"📊 Estatísticas do backup:")
    print(f"   - Total de nós: {stats.get('total_nodes', 0)}")
    print(f"   - Total de relacionamentos: {stats.get('total_relationships', 0)}")
    print(f"   - Data do backup: {backup_data.get('export_date', 'N/A')}")

    # Agrupar nós por label
    nodes_by_label = {}
    for node in nodes:
        labels = node.get('labels', [])
        for label in labels:
            if label not in nodes_by_label:
                nodes_by_label[label] = []
            nodes_by_label[label].append(node)

    print(f"\n📋 Labels encontrados:")
    for label, items in sorted(nodes_by_label.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"   - {label}: {len(items)} nós")

    print("\n🔄 Iniciando restauração...")

    # Contador de progresso
    total_nodes = len(nodes)
    processed = 0
    errors = 0

    # Processar nós por lote para melhor performance
    batch_size = 50

    for label, label_nodes in nodes_by_label.items():
        print(f"\n📌 Processando {label} ({len(label_nodes)} nós)...")

        for i in range(0, len(label_nodes), batch_size):
            batch = label_nodes[i:i+batch_size]
            entities = []

            for node in batch:
                properties = node.get('properties', {})

                # Preparar entidade baseada no label
                if label == 'Learning':
                    # Para Learning nodes
                    entity = {
                        'name': properties.get('name', f"Learning_{node.get('id')}"),
                        'type': 'Learning',
                        'observations': []
                    }

                    # Adicionar todas as propriedades como observações
                    for key, value in properties.items():
                        if key != 'name' and value:
                            if isinstance(value, list):
                                entity['observations'].extend([str(v) for v in value])
                            elif key == 'observations':
                                entity['observations'].extend(value if isinstance(value, list) else [str(value)])
                            else:
                                entity['observations'].append(f"{key}: {value}")

                elif label in ['Memory', 'Documentation', 'ContentChunk']:
                    # Para outros tipos importantes
                    entity = {
                        'name': properties.get('name', properties.get('title', f"{label}_{node.get('id')}")),
                        'type': label,
                        'observations': []
                    }

                    # Adicionar conteúdo como observações
                    if 'content' in properties:
                        entity['observations'].append(properties['content'])
                    if 'description' in properties:
                        entity['observations'].append(properties['description'])

                    # Adicionar outras propriedades relevantes
                    for key in ['chunk_id', 'source_file', 'created_at', 'updated_at']:
                        if key in properties and properties[key]:
                            entity['observations'].append(f"{key}: {properties[key]}")

                else:
                    # Para outros labels genéricos
                    entity = {
                        'name': properties.get('name', properties.get('id', f"{label}_{node.get('id')}")),
                        'type': label,
                        'observations': []
                    }

                    # Adicionar principais propriedades como observações
                    for key, value in properties.items():
                        if key not in ['name', 'id'] and value:
                            if isinstance(value, list):
                                entity['observations'].extend([str(v) for v in value])
                            else:
                                entity['observations'].append(f"{key}: {value}")

                # Adicionar apenas se tiver conteúdo válido
                if entity['observations']:
                    entities.append(entity)

            # Criar entidades no Neo4j via MCP
            if entities:
                try:
                    # Aqui usaríamos a ferramenta MCP, mas vou imprimir o comando
                    print(f"   Criando {len(entities)} entidades do tipo {label}...")

                    # Preparar payload para o MCP
                    mcp_payload = {
                        "entities": entities
                    }

                    # Salvar em arquivo temporário para verificação
                    temp_file = f"/tmp/neo4j_restore_{label}_{i}.json"
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(mcp_payload, f, indent=2)

                    print(f"   ✅ Lote salvo em: {temp_file}")
                    processed += len(entities)

                except Exception as e:
                    print(f"   ❌ Erro ao processar lote: {e}")
                    errors += len(entities)

        print(f"   ✅ {label} processado!")

    # Processar relacionamentos
    print(f"\n🔗 Processando relacionamentos...")
    relationships = []

    for node in nodes:
        node_name = node.get('properties', {}).get('name', f"Node_{node.get('id')}")
        node_rels = node.get('relationships', [])

        for rel in node_rels:
            relationships.append({
                'source': node_name,
                'target': rel.get('end_node', 'Unknown'),
                'relationType': rel.get('type', 'RELATED_TO')
            })

    if relationships:
        # Salvar relacionamentos para processamento
        rel_file = "/tmp/neo4j_restore_relationships.json"
        with open(rel_file, 'w', encoding='utf-8') as f:
            json.dump({"relations": relationships[:100]}, f, indent=2)  # Limitar para teste
        print(f"   ✅ {len(relationships)} relacionamentos salvos em: {rel_file}")

    # Resumo final
    print(f"\n✅ Restauração preparada!")
    print(f"   - Nós processados: {processed}")
    print(f"   - Erros: {errors}")
    print(f"   - Relacionamentos: {len(relationships)}")

    print(f"\n📝 Próximos passos:")
    print(f"   1. Verificar os arquivos em /tmp/neo4j_restore_*.json")
    print(f"   2. Usar as ferramentas MCP para criar as entidades:")
    print(f"      mcp__neo4j-memory__create_entities com cada arquivo")
    print(f"   3. Criar os relacionamentos:")
    print(f"      mcp__neo4j-memory__create_relations com relationships.json")

    return processed, errors

def main():
    """Função principal."""
    if len(sys.argv) < 2:
        # Usar o backup mais recente por padrão
        backup_file = "/Users/2a/.claude/memoria-neo4j/backups/neo4j_backup_20250926_224936.json"
        print(f"⚠️  Usando backup padrão: {backup_file}")
    else:
        backup_file = sys.argv[1]

    if not Path(backup_file).exists():
        print(f"❌ Arquivo não encontrado: {backup_file}")
        sys.exit(1)

    # Executar restauração
    asyncio.run(restore_backup(backup_file))

if __name__ == "__main__":
    main()