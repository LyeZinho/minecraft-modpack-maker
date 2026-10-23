# Modpack Fixer — Fase 1: núcleo determinístico

Ferramenta autônoma para criar, corrigir e manter modpacks de Minecraft com suporte a **Modrinth** (e, depois, **CurseForge com chave do usuário**).

> **Regra de arquitetura (não negociável):** o LLM nunca escolhe versão nem nome de mod.  
> Quem decide compatibilidade é o **solver determinístico** sobre metadados da Modrinth (`dependency_type`, `game_versions`, `loaders`, hash SHA-512).  
> O LLM entra só para interpretar stack traces, escrever patches de config e explicar o que mudou.

## O que este esqueleto já faz

1. **Busca de mods**: `search` combina a API da Modrinth + DuckDuckGo para descobrir slugs a partir de linguagem natural (ex: "automação fabric 1.20.1"), sem exigir que o usuário conheça nomes exatos de projetos.
2. **Ingestão de metadados** da API pública da Modrinth (sem chave, sem cadastro).
3. **Resolução determinística de dependências**: entrada = lista de slugs + versão do jogo + loader; saída = grafo de mods com versões escolhidas.
4. **Lockfile reprodutível** (`lockfile.json` compatível com `modrinth.index.json` + `pack.toml`) com hashes SHA-512 de cada arquivo — permite reconstruir o pack byte a byte e fazer diff entre versões.
5. **Export `.mrpack`**: ZIP com o `modrinth.index.json` na raiz, pronto para ser aberto por launchers compatíveis. Os JARs são baixados das URLs oficiais pelo launcher — nunca redistribuímos arquivos próprios.

## Instalação

```bash
# Na raiz do projeto
pip install -e .

# Ou apenas rode o módulo direto, sem instalar
python -m modpack_fixer --help
```

## Uso (Fase 1)

### 0) Buscar mods (quando você não conhece o slug exato)

```bash
python -m modpack_fixer search \
    --query "automacao fabric 1.20.1" \
    --game-version 1.20.1 \
    --loader fabric \
    --limit 10
```

A busca combina a **API da Modrinth** (dados estruturados: slug, downloads, descrição) com o **DuckDuckGo** (descoberta adicional). O resultado inclui o slug que você passa para o `resolve`.

### 1) Resolver dependências e gerar pack local

```bash
python -m modpack_fixer resolve \
    --mods jei,create \
    --game-version 1.20.1 \
    --loader fabric \
    --name "Meu Pack de Teste" \
    --output ./pack
```

### 2) Exportar .mrpack

```bash
python -m modpack_fixer export \
    --lockfile ./pack/lockfile.json \
    --output ./pack.mrpack
```

### Fluxo agentico completo (exemplo)

```bash
# Busca → pega o slug sugerido → resolve → exporta
python -m modpack_fixer search --query "jei fabric 1.20.1" --limit 1
# slug sugerido: jei
python -m modpack_fixer resolve --mods jei --game-version 1.20.1 --loader fabric --output ./pack
python -m modpack_fixer export --lockfile ./pack/lockfile.json --output ./pack.mrpack
```

Saída em `./pack/`:
- `lockfile.json` → manifesto com todos os mods, URLs oficiais, hashes SHA-512 e tamanhos.
- `pack.toml` → metadados legíveis (nome, versão, jogo, loader, data de criação).

## Próximas fases (roadmap)

| Fase | Objetivo | Status |
|------|----------|--------|
| 1 | Busca de mods (Modrinth API + DuckDuckGo) + slug discovery | ✅ |
| 1 | Solver determinístico + lockfile + export `.mrpack` | ✅ |
| 2 | Sandbox Docker headless com JVM; primeiro boot e coleta de logs | Em planejamento |
| 3 | Analisador de crash (regex + LLM apenas quando regex não basta) | Em planejamento |
| 4 | Agent de reparo automático (atualizar/remover/adicionar mod + re-resolver) | Em planejamento |
| 5 | Suporte a CurseForge com chave do usuário (não chave central) | Em planejamento |
| 6 | Edição de configs/KubeJS/datapack e upgrade de pack entre versões do MC | Em planejamento |

## Filosofia de design (resumo da pesquisa)

- **Criar vs corrigir são produtos diferentes.** Este MVP foca na correção/manutenção de packs existentes para donos de servidor (dor real, dispostos a pagar).
- **Não redistribuir JARs.** O manifest aponta para URLs oficiais; o launcher baixa. Isso respeita termos da CurseForge e licenças dos autores.
- **Benchmark primeiro.** Antes de expandir, montar 20–50 packs reais quebrados com causa conhecida para medir taxa de "bootou verde", não demo bonita.

## Licença

Privado / uso interno. Adicione uma licença adequada antes de publicar.
