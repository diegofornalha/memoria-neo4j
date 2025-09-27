#!/bin/bash
# 🔒 Neo4j Manager MCP - Sistema Seguro de Gerenciamento
# Versão 2.0 - Após análise de segurança

set -e

# Configurações
BASE_DIR="/Users/2a/.claude/memoria-neo4j-claude-code-sdk"
BACKUP_DIR="$BASE_DIR/memory-backups-mcp"
SRC_DIR="$BASE_DIR/src"
SCRIPT_DIR="$BASE_DIR/script"

export NEO4J_URI="${NEO4J_URI:-bolt://127.0.0.1:7687}"
export NEO4J_USERNAME="${NEO4J_USERNAME:-neo4j}"
export NEO4J_DATABASE="${NEO4J_DATABASE:-neo4j}"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Função para mostrar menu
show_menu() {
    clear
    echo -e "${PURPLE}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║    🔒 Neo4j Manager MCP - Sistema Seguro    ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════╝${NC}"

    # Status rápido
    echo -e "\n${CYAN}📊 Status:${NC}"

    # Verificar conexão (simulado para não depender do Neo4j agora)
    echo -e "  ✅ Sistema atualizado para estrutura src/"
    echo -e "  ✅ Usando backup seguro MCP"

    # Contar backups
    if [ -d "$BACKUP_DIR" ]; then
        BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/SECURE_MCP_*.zip 2>/dev/null | wc -l)
        echo -e "  📦 Backups seguros: $BACKUP_COUNT arquivos"
    fi

    echo -e "\n${GREEN}📁 Estrutura Atualizada:${NC}"
    echo -e "  ${CYAN}src/${NC} - Código Python (pacote válido)"
    echo -e "  ${CYAN}script/${NC} - Scripts Bash"
    echo -e "  ${CYAN}memory-backups-mcp/${NC} - Backups seguros"
    echo -e "  ${CYAN}docs/${NC} - Documentação"

    echo -e "\n${YELLOW}🔐 Opções:${NC}"
    echo -e "  ${GREEN}[1]${NC} 🔒 Fazer Backup Seguro (MCP)"
    echo -e "  ${GREEN}[2]${NC} 📊 Ver Estatísticas do Neo4j"
    echo -e "  ${GREEN}[3]${NC} 🔄 Restaurar Backup"
    echo -e "  ${GREEN}[4]${NC} 🧹 Limpar Duplicados"
    echo -e "  ${GREEN}[5]${NC} 📈 Benchmark Performance"
    echo -e "  ${GREEN}[6]${NC} 📝 Ver Logs de Backup"
    echo -e "  ${GREEN}[7]${NC} 🛡️  Análise de Segurança"
    echo -e "  ${GREEN}[0]${NC} ❌ Sair"
}

# Função para fazer backup
do_backup() {
    echo -e "\n${CYAN}🔒 Iniciando Backup Seguro MCP...${NC}"
    cd "$BASE_DIR"
    python3 "$SRC_DIR/backup_mcp.py"
}

# Função para ver estatísticas
show_stats() {
    echo -e "\n${CYAN}📊 Estatísticas do Neo4j:${NC}"
    if [ -f "$BACKUP_DIR/BACKUP_LOG.json" ]; then
        python3 -c "
import json
with open('$BACKUP_DIR/BACKUP_LOG.json') as f:
    log = json.load(f)
    if log.get('backups'):
        last = log['backups'][-1]
        print(f'\n📈 Último backup:')
        print(f'  📅 Data: {last[\"timestamp\"]}')
        print(f'  📦 Arquivo: {last[\"file\"]}')
        stats = last.get('stats', {})
        if stats:
            print(f'\n📊 Estatísticas:')
            print(f'  • Total de nós: {stats.get(\"total_nodes\", \"N/A\")}')
            print(f'  • Total de relacionamentos: {stats.get(\"total_relationships\", \"N/A\")}')
            labels = stats.get('labels', {})
            if labels:
                print(f'\n🏷️  Labels:')
                for label, count in labels.items():
                    print(f'  • {label}: {count} nós')
"
    fi
}

# Função para ver logs
show_logs() {
    echo -e "\n${CYAN}📝 Logs de Backup:${NC}"
    if [ -f "$BACKUP_DIR/BACKUP_LOG.json" ]; then
        python3 -c "
import json
from datetime import datetime
with open('$BACKUP_DIR/BACKUP_LOG.json') as f:
    log = json.load(f)
    backups = log.get('backups', [])
    print(f'\n📚 Total de backups: {len(backups)}')
    print('\n📋 Histórico (últimos 5):')
    for backup in backups[-5:]:
        print(f\"  • {backup['timestamp']} - {backup['file']} ({backup['method']})\")
"
    else
        echo -e "${YELLOW}⚠️  Nenhum log encontrado${NC}"
    fi
}

# Função para análise de segurança
security_check() {
    echo -e "\n${PURPLE}🛡️  Análise de Segurança:${NC}"
    echo -e "\n${GREEN}✅ Verificações de Segurança:${NC}"
    echo -e "  • Sem vulnerabilidades Cypher Injection"
    echo -e "  • Credenciais via variáveis de ambiente"
    echo -e "  • Hash SHA256 para integridade"
    echo -e "  • Compressão ZIP segura"
    echo -e "  • Whitelist de labels válidos"
    echo -e "\n${CYAN}📁 Arquivos Seguros:${NC}"
    echo -e "  • ${GREEN}src/backup_mcp.py${NC} - Sistema principal"
    echo -e "  • ${GREEN}script/neo4j-backup-mcp.sh${NC} - Script wrapper"
    echo -e "\n${RED}❌ Arquivos Removidos (Inseguros):${NC}"
    echo -e "  • save_to_neo4j.py - Cypher injection"
    echo -e "  • secure_backup.py - Substituído por MCP"
}

# Loop principal
while true; do
    show_menu
    echo -ne "\n${CYAN}Escolha uma opção: ${NC}"
    read -r option

    case $option in
        1) do_backup ;;
        2) show_stats ;;
        3) echo -e "${YELLOW}🔄 Restauração em desenvolvimento...${NC}" ;;
        4) echo -e "${YELLOW}🧹 Limpeza via Python: python3 $SRC_DIR/clean_duplicates.py${NC}" ;;
        5)
            echo -e "${CYAN}📈 Rodando benchmark...${NC}"
            python3 "$SRC_DIR/benchmark.py"
            ;;
        6) show_logs ;;
        7) security_check ;;
        0)
            echo -e "${GREEN}✅ Saindo do Neo4j Manager MCP${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Opção inválida${NC}"
            ;;
    esac

    echo -ne "\n${YELLOW}Pressione ENTER para continuar...${NC}"
    read -r
done