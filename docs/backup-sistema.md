# 🔒 Sistema de Backup Neo4j MCP v3.0

## 📋 Visão Geral

Sistema completo de backup para Neo4j com exportação de **TODOS** os nós e relacionamentos do grafo de conhecimento.

### ✨ Características

- ✅ **Backup Completo**: Exporta 100% dos dados (1.027 nós + 538 relacionamentos)
- 🔄 **Paginação Inteligente**: Processa dados em lotes de 100 registros
- 🗜️ **Compressão ZIP**: Reduz tamanho em ~80% (0.9MB → 0.19MB)
- 🔒 **Hash SHA256**: Verificação de integridade
- 📊 **Estatísticas Detalhadas**: 138 labels únicos catalogados
- 🚀 **Performance**: ~340 nós/segundo

## 🛠️ Como Usar

### Método 1: Script Bash (Recomendado)
```bash
cd /Users/2a/.claude/memoria-neo4j
bash script/neo4j-backup-mcp.sh
```

### Método 2: Script Python Direto
```bash
cd /Users/2a/.claude/memoria-neo4j
python3 script/neo4j-backup-complete.py
```

### Método 3: Com Variáveis de Ambiente
```bash
NEO4J_PASSWORD="sua_senha" bash script/neo4j-backup-mcp.sh
```

## 📁 Estrutura de Arquivos

```
memoria-neo4j/
├── script/
│   ├── neo4j-backup-mcp.sh        # Script principal (bash)
│   └── neo4j-backup-complete.py   # Motor de backup (Python)
├── backups/
│   ├── neo4j_backup_*.json        # Backups em JSON
│   ├── neo4j_backup_*.zip         # Backups comprimidos
│   └── BACKUP_LOG.json            # Log de todos os backups
└── docs/
    └── backup-sistema.md          # Esta documentação
```

## 🔧 Configuração

### Variáveis de Ambiente
```bash
NEO4J_URI=bolt://127.0.0.1:7687    # Endereço do Neo4j
NEO4J_USERNAME=neo4j               # Usuário
NEO4J_PASSWORD=password            # Senha
NEO4J_DATABASE=neo4j               # Database
```

### Arquivo .env (Opcional)
Crie um arquivo `.env` no diretório raiz:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j
```

## 📊 Formato do Backup

### Estrutura JSON
```json
{
  "export_timestamp": "2025-09-26T22:49:36",
  "export_date": "2025-09-26 22:49:36",
  "statistics": {
    "total_nodes": 1027,
    "total_relationships": 538,
    "labels": [...],
    "relationship_types": [...]
  },
  "nodes": [
    {
      "id": 123,
      "labels": ["Learning"],
      "properties": {...}
    }
  ],
  "relationships": [
    {
      "id": 456,
      "start_id": 123,
      "end_id": 789,
      "type": "KNOWS",
      "properties": {...}
    }
  ]
}
```

## 📈 Estatísticas Típicas

### Top Labels no Sistema
1. **Learning**: 544 nós (53% do total)
2. **ContentChunk**: 216 nós (21%)
3. **Keyword**: 85 nós (8%)
4. **Memory**: 45 nós (4%)
5. **SuccessfulExecution**: 39 nós (4%)

### Métricas de Performance
- **Taxa de Exportação**: ~340 nós/segundo
- **Tempo Total**: ~3-5 segundos para backup completo
- **Compressão**: 80% de redução (JSON → ZIP)
- **Memória Usada**: < 50MB durante processamento

## 🔄 Restauração

### Restaurar de Backup JSON
```python
from neo4j import GraphDatabase
import json

# Carregar backup
with open('backups/neo4j_backup_20250926_224936.json') as f:
    backup = json.load(f)

# Conectar ao Neo4j
driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password")
)

# Restaurar nós
with driver.session() as session:
    for node in backup['nodes']:
        labels = ':'.join(node['labels'])
        query = f"CREATE (n:{labels} $props)"
        session.run(query, props=node['properties'])

# Restaurar relacionamentos
# ... (implementação similar)
```

## 🛡️ Segurança

### Práticas Implementadas
- ✅ **Sem Cypher Injection**: Queries parametrizadas
- ✅ **Credenciais Seguras**: Via variáveis de ambiente
- ✅ **Integridade**: Hash SHA256 para cada backup
- ✅ **Compressão Segura**: ZIP com deflate
- ✅ **Logs Auditáveis**: BACKUP_LOG.json com histórico

### Avisos de Deprecação
O Neo4j está migrando de `id()` para `elementId()`. Os avisos são normais e não afetam o backup.

## 🚀 Melhorias Futuras

1. **Backup Incremental**: Apenas mudanças desde o último backup
2. **Criptografia**: Opção para criptografar backups
3. **Cloud Storage**: Upload automático para S3/GCS
4. **Restore Automático**: Script de restauração completa
5. **Migração elementId**: Atualizar para novo sistema de IDs

## 📝 Changelog

### v3.0 (2025-09-26)
- ✅ Backup completo com todos os nós (1.027)
- ✅ Paginação para grandes volumes
- ✅ Compressão ZIP automática
- ✅ Log de backups persistente

### v2.0 (2025-09-22)
- Sistema seguro MCP inicial
- Proteção contra Cypher Injection

### v1.0 (2025-09-17)
- Primeira versão do sistema

## 🆘 Troubleshooting

### Erro de Autenticação
```bash
# Verificar senha correta
echo $NEO4J_PASSWORD

# Usar senha padrão
NEO4J_PASSWORD="password" bash script/neo4j-backup-mcp.sh
```

### Neo4j Não Conecta
```bash
# Verificar se Neo4j está rodando
neo4j status

# Verificar porta
lsof -i :7687
```

### Backup Muito Grande
- Aumentar `batch_size` no script Python (linha 66)
- Considerar backup por labels específicos
- Usar compressão adicional

## 📞 Suporte

Para issues ou melhorias, abrir ticket em:
- `/Users/2a/.claude/memoria-neo4j/issues/`
- Ou criar memória no Neo4j com label "BugReport"