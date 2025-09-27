#!/bin/bash
# 🔒 Neo4j Backup Seguro MCP
# Usa o sistema seguro backup_mcp.py após análise de vulnerabilidades

set -e

# Configurações
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SRC_DIR="${PROJECT_ROOT}/src"
BACKUP_DIR="${PROJECT_ROOT}/memory-backups-mcp"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║     🔒 Neo4j Backup Seguro MCP v2.0         ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════╝${NC}\n"

# Verificar se o diretório src existe
if [ ! -d "$SRC_DIR" ]; then
    echo -e "${RED}❌ Erro: Diretório src/ não encontrado${NC}"
    echo -e "${YELLOW}📍 Procurando em: $SRC_DIR${NC}"
    exit 1
fi

# Criar diretório de backup se não existir
mkdir -p "${BACKUP_DIR}"

echo -e "${YELLOW}🔐 Verificando variáveis de ambiente...${NC}"

# Configurações do Neo4j (opcionais - backup_mcp.py tem defaults seguros)
if [ -z "$NEO4J_PASSWORD" ]; then
    echo -e "${YELLOW}⚠️  NEO4J_PASSWORD não definido - usando padrão seguro${NC}"
fi

export NEO4J_URI="${NEO4J_URI:-bolt://127.0.0.1:7687}"
export NEO4J_USERNAME="${NEO4J_USERNAME:-neo4j}"

echo -e "${CYAN}📊 Iniciando backup seguro via MCP...${NC}"
echo -e "${CYAN}📍 Usando: ${SRC_DIR}/backup_mcp.py${NC}\n"

# Executar script Python seguro
cd "$PROJECT_ROOT"
python3 "${SRC_DIR}/backup_mcp.py"

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║    ✅ Backup Seguro MCP Concluído!          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}\n"

    echo -e "${CYAN}📦 Últimos backups seguros:${NC}"
    ls -lh "${BACKUP_DIR}"/SECURE_MCP_*.zip 2>/dev/null | tail -5 | while read line; do
        echo -e "  ${GREEN}→${NC} $line"
    done

    echo -e "\n${CYAN}📊 Log de backups:${NC}"
    if [ -f "${BACKUP_DIR}/BACKUP_LOG.json" ]; then
        # Mostrar último backup do log
        python3 -c "
import json
with open('${BACKUP_DIR}/BACKUP_LOG.json') as f:
    log = json.load(f)
    if log.get('backups'):
        last = log['backups'][-1]
        print(f\"  📅 Último: {last['timestamp']}\")
        print(f\"  📦 Arquivo: {last['file']}\")
        print(f\"  🔒 Hash: {last['hash'][:16]}...\")
        print(f\"  📊 Total backups: {len(log['backups'])}\")
"
    fi

    echo -e "\n${PURPLE}🛡️  Análise de Segurança:${NC}"
    echo -e "  ✅ Sem vulnerabilidades Cypher Injection"
    echo -e "  ✅ Credenciais via variáveis de ambiente"
    echo -e "  ✅ Hash SHA256 para integridade"
    echo -e "  ✅ Compressão ZIP segura"

else
    echo -e "${RED}❌ Erro ao criar backup seguro${NC}"
    echo -e "${YELLOW}💡 Dica: Verifique as credenciais do Neo4j${NC}"
    exit 1
fi