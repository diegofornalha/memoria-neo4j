# Como Parar de Seguir Automaticamente Pessoas no LinkedIn

## O Problema

Posts de "**fulano gostou disso**" aparecem constantemente no feed do LinkedIn, mostrando conteúdo de pessoas que você não segue diretamente.

## A Solução

Automatizar o processo de parar de seguir essas pessoas usando **Chrome DevTools MCP**.

---

## Pré-requisitos

✅ Chrome DevTools MCP instalado e configurado
✅ LinkedIn aberto e autenticado no navegador
✅ Claude Code rodando

---

## Passo a Passo

### 1. Abrir o LinkedIn no Chrome DevTools

```javascript
// No Claude Code, peça para abrir o LinkedIn
"Abra o LinkedIn via Chrome DevTools"
```

Ou use o comando MCP diretamente:
```javascript
mcp__chrome-devtools__navigate_page({
  type: "url",
  url: "https://www.linkedin.com/feed/"
})
```

### 2. Executar o Script de Automação

Cole e execute este script no Chrome DevTools:

```javascript
async () => {
  const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  const results = {
    unfollowed: [],
    errors: []
  };

  const processLikedPosts = async () => {
    // Encontrar todos os textos "gostou disso"
    const textNodes = [];
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      null
    );

    let node;
    while (node = walker.nextNode()) {
      const text = node.textContent.trim();
      if (text.includes('gostou disso') || text.includes('achou isso')) {
        textNodes.push(node.parentElement);
      }
    }

    // Processar cada post
    for (let textEl of textNodes) {
      try {
        // Subir na árvore DOM para encontrar o container do post
        let container = textEl;
        let menuButton = null;

        for (let i = 0; i < 20; i++) {
          container = container.parentElement;
          if (!container) break;

          // Procurar botão de menu (3 pontos)
          menuButton = container.querySelector('button[aria-label*="Ver mais opções"]') ||
                      container.querySelector('button[aria-label*="opções"]');

          if (menuButton && (container.innerText.includes('gostou disso') ||
                            container.innerText.includes('achou isso'))) {
            break;
          }
        }

        if (menuButton) {
          // Extrair nome da pessoa
          const personName = textEl.textContent.split('gostou disso')[0]
                                               .split('achou isso')[0]
                                               .trim();

          // Rolar até o botão e clicar
          menuButton.scrollIntoView({ behavior: 'smooth', block: 'center' });
          await wait(500);
          menuButton.click();
          await wait(1200);

          // Procurar opção "Parar de seguir" no menu
          const menuItems = Array.from(document.querySelectorAll('[role="menu"] *'));

          for (let item of menuItems) {
            const itemText = item.textContent || '';

            if (itemText.includes('Parar de seguir') ||
                itemText.includes('Deixar de seguir')) {

              const clickable = item.closest('button') ||
                              item.closest('[role="menuitem"]') ||
                              item.closest('div[role="button"]') ||
                              item;

              clickable.click();
              results.unfollowed.push(personName);
              await wait(800);
              break;
            }
          }

          // Fechar menu
          try {
            document.body.click();
          } catch (e) {}

          await wait(800);
        }
      } catch (error) {
        results.errors.push(error.message);
      }
    }
  };

  // Executar múltiplas rodadas com scroll
  for (let round = 0; round < 5; round++) {
    await processLikedPosts();
    window.scrollBy(0, 1000);
    await wait(2000);
  }

  return {
    unfollowed: results.unfollowed,
    count: results.unfollowed.length,
    errors: results.errors.slice(0, 5)
  };
}
```

### 3. Executar via Claude Code

Você pode pedir ao Claude Code para executar o script:

```
"Execute o script para parar de seguir pessoas nos posts 'gostou disso' do LinkedIn"
```

O Claude vai usar o Chrome DevTools MCP para executar automaticamente.

---

## Como Funciona

1. **Identificação**: O script procura por textos contendo "gostou disso" ou "achou isso" no feed
2. **Navegação DOM**: Sobe na árvore de elementos para encontrar o container completo do post
3. **Menu**: Localiza e clica no botão de menu (3 pontos)
4. **Ação**: Clica em "Parar de seguir" no menu suspenso
5. **Loop**: Rola a página e repete o processo

---

## Resultados do Teste

Testado com sucesso e parou de seguir **5 pessoas**:
- ✅ Lucas Gusmão
- ✅ Eduardo Ramon Resser
- ✅ Ricardo Borges Almeida Moraes
- ✅ Yuri Sampaio
- ✅ Bruno Contardi ₿

---

## Personalização

### Ajustar número de rodadas

Altere este valor para processar mais ou menos posts:

```javascript
for (let round = 0; round < 5; round++) { // ← Altere o 5
```

### Ajustar velocidade

Modifique os tempos de espera (em milissegundos):

```javascript
await wait(500);  // Tempo de scroll
await wait(1200); // Tempo para menu abrir
await wait(800);  // Tempo após clicar
await wait(2000); // Tempo após scroll
```

### Adicionar mais variações de texto

Adicione outras frases que aparecem no seu feed:

```javascript
if (text.includes('gostou disso') ||
    text.includes('achou isso') ||
    text.includes('comentou isso') ||  // ← Adicione aqui
    text.includes('celebrou isso')) {
```

---

## Dicas

💡 **Execute em horários diferentes** - O algoritmo do LinkedIn mostra pessoas diferentes em horários variados

💡 **Recarregue a página** - Entre execuções, recarregue o feed para carregar novos posts

💡 **Use com moderação** - Execute algumas vezes por dia para não parecer comportamento de bot

💡 **Combine com filtros** - Ajuste suas preferências de feed nas configurações do LinkedIn

---

## Segurança

⚠️ Este script apenas automatiza cliques que você faria manualmente
⚠️ Não coleta dados nem envia informações para fora
⚠️ Roda localmente no seu navegador via Chrome DevTools MCP
⚠️ Respeita os limites de velocidade do LinkedIn (delays entre ações)

---

## Troubleshooting

### Script não encontra botões

**Solução**: O LinkedIn pode ter mudado a estrutura HTML. Atualize os seletores:

```javascript
// Procure por:
menuButton = container.querySelector('button[aria-label*="NOVO_TEXTO_AQUI"]')
```

### LinkedIn mostra captcha

**Solução**: Você está executando muito rápido. Aumente os delays e reduza o número de rodadas.

### Erro "Maximum call stack"

**Solução**: Recarregue a página antes de executar novamente.

---

## Integração com Claude Code

### Criar comando customizado

Crie um arquivo `.claude/commands/unfollow-linkedin.md`:

```markdown
Execute o script de automação para parar de seguir pessoas nos posts "gostou disso" do LinkedIn.

Use o Chrome DevTools MCP para:
1. Navegar até https://www.linkedin.com/feed/
2. Executar o script de automação
3. Reportar quantas pessoas foram deixadas de seguir
```

Depois use: `/unfollow-linkedin`

---

## Roadmap Futuro

- [ ] Adicionar blacklist de pessoas para nunca deixar de seguir
- [ ] Criar whitelist de tipos de conteúdo para manter
- [ ] Exportar relatório de quem foi deixado de seguir
- [ ] Integração com LinkedIn MCP Server
- [ ] Dashboard de estatísticas

---

## Contribuindo

Encontrou um problema ou tem uma sugestão?
Abra uma issue ou envie um PR!

---

## Licença

MIT License - Use livremente!

---

## Créditos

Criado usando:
- **Claude Code** - https://claude.ai/claude-code
- **Chrome DevTools MCP** - https://github.com/executeautomation/chrome-devtools-mcp
- **MCP Protocol** - https://modelcontextprotocol.io/

---

**Última atualização:** 2025-11-09
**Versão:** 1.0.0
