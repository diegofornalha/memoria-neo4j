# Backup Neo4j - Claude Code SDK Memory

## 📊 Resumo da Exportação

**Data:** 2025-09-26 21:14:11  
**Arquivo:** neo4j_backup_20250926_211411.json  
**Tamanho:** 970 KB

### Estatísticas

- **Total de Nós:** 1027
- **Total de Relacionamentos:** 538
- **Labels Únicos:** 138

### Top 10 Labels

1. Learning: 544 nós
2. ContentChunk: 216 nós
3. Keyword: 85 nós
4. Memory: 45 nós
5. SuccessfulExecution: 39 nós
6. Documentation: 20 nós
7. Error: 9 nós
8. architecture: 8 nós
9. best_practice: 8 nós
10. Exercise: 7 nós

## 🔧 Como Restaurar

```bash
# Usando o script de restauração
cd /Users/2a/.claude/memoria-neo4j-claude-code-sdk/backups
export NEO4J_PASSWORD="password"
python3 restore_neo4j.py neo4j_backup_20250926_211411.json
```

## 📁 Estrutura do Backup

O arquivo JSON contém:

- `export_timestamp`: Data/hora da exportação
- `statistics`: Estatísticas do banco
- `nodes`: Array com todos os nós
  - `id`: ID interno do nó
  - `labels`: Labels do nó
  - `properties`: Propriedades do nó
  - `relationships`: Relacionamentos do nó
- `metadata`: Metadados da exportação

## 🎯 Conteúdo Principal

O backup contém principalmente:

- **Aprendizados** (Learning): Conhecimentos e experiências acumuladas
- **Documentação** (ContentChunk, Documentation): Chunks de documentação indexados
- **Execuções** (SuccessfulExecution, FailedExecution): Histórico de tarefas
- **Memórias** (Memory): Memórias estruturadas
- **Exercícios** (Exercise, Lesson): Material educacional
- **Arquitetura** (architecture, best_practice): Decisões e padrões

## 📝 Script de Exportação

O script `export_neo4j_direct.py` foi usado para:

1. Conectar diretamente ao Neo4j via bolt://localhost:7687
2. Fazer queries paginadas de 100 nós por vez
3. Exportar nós com todas as propriedades e relacionamentos
4. Converter tipos Neo4j (DateTime) para JSON
5. Salvar tudo em um arquivo JSON estruturado

## ⚡ Performance

- Tempo de exportação: ~3 segundos
- Taxa de processamento: ~340 nós/segundo
- Método: Conexão direta via neo4j-driver
