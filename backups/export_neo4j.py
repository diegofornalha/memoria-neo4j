#!/usr/bin/env python3
"""
Script para exportar todos os dados do Neo4j usando MCP tools
Faz consultas paginadas por label para evitar limite de tokens
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def run_mcp_search(label=None, limit=50):
    """Executa busca no Neo4j via MCP usando claude-code"""
    cmd = ["claude-code", "--headless"]

    if label:
        prompt = f'Use a ferramenta mcp__neo4j-memory__search_memories com label="{label}" e limit={limit} e depth=2'
    else:
        prompt = f'Use a ferramenta mcp__neo4j-memory__search_memories com limit={limit} e depth=2'

    cmd.extend(["--prompt", prompt])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            return result.stdout
        else:
            print(f"Erro ao buscar {label}: {result.stderr}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Exceção ao buscar {label}: {e}", file=sys.stderr)
        return None

def get_all_labels():
    """Obtém lista de todos os labels no Neo4j"""
    cmd = ["claude-code", "--headless", "--prompt",
           "Use a ferramenta mcp__neo4j-memory__list_memory_labels"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            # Parse output para extrair labels
            output = result.stdout
            labels = []

            # Tenta extrair labels do output
            for line in output.split('\n'):
                if '"label":' in line and '"count":' in line:
                    # Extrai o label da linha JSON
                    try:
                        parts = line.split('"label":')
                        if len(parts) > 1:
                            label_part = parts[1].split(',')[0].strip().strip('"')
                            labels.append(label_part)
                    except:
                        pass

            return labels
        return []
    except Exception as e:
        print(f"Erro ao obter labels: {e}", file=sys.stderr)
        return []

def main():
    """Função principal de exportação"""
    print("🚀 Iniciando exportação do Neo4j...")

    # Lista de labels conhecidos (baseado na saída anterior)
    labels = [
        "Learning", "ContentChunk", "Keyword", "Memory", "SuccessfulExecution",
        "Documentation", "Error", "architecture", "best_practice", "Exercise",
        "Lesson", "FailedExecution", "BestPractice", "component", "concept",
        "Rule", "Example", "integration", "Agent", "configuration", "example",
        "technique", "documentation", "use_case", "hello_world_example",
        "project", "solution", "evaluation_task", "QuizResult", "Category",
        "Concept", "translation", "knowledge", "command", "lesson",
        "bash_script_example", "agent_config", "critical_thinking", "improvement",
        "implementation_step", "project_organization", "Problem"
    ]

    print(f"📊 Labels a exportar: {len(labels)}")

    all_data = {
        "export_timestamp": datetime.now().isoformat(),
        "labels": {},
        "metadata": {
            "total_labels": len(labels),
            "export_method": "mcp_paginated"
        }
    }

    # Exporta cada label separadamente
    for i, label in enumerate(labels, 1):
        print(f"📥 [{i}/{len(labels)}] Exportando label '{label}'...", end=" ")

        # Tenta com limite de 50 primeiro
        data = run_mcp_search(label=label, limit=50)

        if data:
            all_data["labels"][label] = {
                "raw_output": data,
                "exported_at": datetime.now().isoformat()
            }
            print("✅")
        else:
            print("❌")

    # Salva arquivo JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path(__file__).parent / f"neo4j_backup_{timestamp}.json"

    print(f"\n💾 Salvando backup em: {output_file}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Backup completo salvo!")
    print(f"📁 Arquivo: {output_file}")
    print(f"📊 Total de labels exportados: {len([k for k, v in all_data['labels'].items() if v])}")

if __name__ == "__main__":
    main()