#!/bin/bash
# 🗑️ Neo4j Clean MCP - Limpeza Segura do Banco de Dados
# Versão atualizada para estrutura src/

set -e

# Configurações
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SRC_DIR="${PROJECT_ROOT}/src"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configurações Neo4j
export NEO4J_URI="${NEO4J_URI:-bolt://127.0.0.1:7687}"
export NEO4J_USERNAME="${NEO4J_USERNAME:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"
export NEO4J_DATABASE="${NEO4J_DATABASE:-neo4j}"

echo -e "${RED}╔══════════════════════════════════════════════╗${NC}"
echo -e "${RED}║     🗑️  Neo4j Clean MCP - Limpeza Segura    ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════╝${NC}\n"

# Verificar estrutura
if [ ! -d "$SRC_DIR" ]; then
    echo -e "${RED}❌ Erro: Diretório src/ não encontrado${NC}"
    echo -e "${YELLOW}📍 Esperado em: $SRC_DIR${NC}"
    exit 1
fi

# Script Python para limpeza
cat > "$SRC_DIR/neo4j_clean_temp.py" << 'EOF'
#!/usr/bin/env python3
"""Limpeza segura do Neo4j com confirmação"""

import os
from neo4j import GraphDatabase

# Configurações
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

try:
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )

    with driver.session(database=NEO4J_DATABASE) as session:
        # Estatísticas atuais
        stats = session.run("""
            MATCH (n)
            WITH count(n) as nodes
            MATCH ()-[r]->()
            RETURN nodes, count(r) as rels
        """).single()

        if stats:
            print(f"📊 Estado atual do banco:")
            print(f"   • Nós: {stats['nodes']}")
            print(f"   • Relacionamentos: {stats['rels']}")

            if stats['nodes'] == 0 and stats['rels'] == 0:
                print("\n✅ O banco já está vazio!")
                exit(0)

            # Mostrar labels que serão removidos
            labels = session.run("""
                MATCH (n)
                UNWIND labels(n) as label
                RETURN DISTINCT label, count(n) as count
                ORDER BY count DESC
                LIMIT 10
            """)

            print("\n🏷️  Labels que serão removidos:")
            for record in labels:
                print(f"   • {record['label']}: {record['count']} nós")

            print(f"\n⚠️  AVISO: {stats['nodes']} nós e {stats['rels']} relacionamentos serão DELETADOS!")
            confirm = input("Digite 'CONFIRMAR' para prosseguir: ")

            if confirm == 'CONFIRMAR':
                print("\n🗑️  Limpando banco de dados...")

                # Deletar tudo
                session.run("MATCH (n) DETACH DELETE n")

                # Verificar
                check = session.run("MATCH (n) RETURN count(n) as count").single()

                if check['count'] == 0:
                    print("✅ Banco limpo com sucesso!")
                else:
                    print(f"⚠️  Ainda restam {check['count']} nós")
            else:
                print("\n❌ Limpeza cancelada")
                exit(1)
        else:
            print("✅ Banco vazio")

    driver.close()

except Exception as e:
    print(f"❌ Erro: {e}")
    exit(1)
EOF

# Executar script Python
echo -e "${CYAN}🔍 Conectando ao Neo4j...${NC}\n"
python3 "$SRC_DIR/neo4j_clean_temp.py"

# Limpar arquivo temporário
rm -f "$SRC_DIR/neo4j_clean_temp.py"

echo -e "\n${PURPLE}💡 Dicas:${NC}"
echo -e "   • Para fazer backup antes de limpar: ${GREEN}./neo4j-backup-mcp.sh${NC}"
echo -e "   • Para restaurar depois: ${GREEN}./neo4j-restore-mcp.sh${NC}"
echo -e "   • Para gerenciar o banco: ${GREEN}./neo4j-manager-mcp.sh${NC}"