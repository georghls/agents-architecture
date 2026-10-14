# Registro de decisões

Use entradas curtas com data, contexto, escolha, alternativas, consequência e status. **Não interprete sugestões das conversas como tecnologias já instaladas.**

## Confirmado pelo planejamento acadêmico

| ID | Decisão/requisito | Origem |
|---|---|---|
| P-01 | Projetar, implementar e monitorar sistema multiagente conectado a dados por MCP | Planejamento original, objetivo geral |
| P-02 | Fases 1–5: desenho, integração segura/MCP, agentes, LLMOps, relatório | Planejamento original, metodologia |
| P-03 | Repositório, dashboard e relatório técnico; interface consta nos objetivos | Planejamento original, objetivos e entregáveis |

## Confirmado nas conversas de estudo

| ID | Direção | Observação |
|---|---|---|
| C-01 | Cenário: perguntas sobre documentos corporativos | Usar dados sintéticos na primeira versão |
| C-02 | Comparar Coordenador, Plano–Executor e Conversação em Grupo | Blackboard foi uma ideia anterior, depois substituída |
| C-03 | Estudar LangGraph para os dois primeiros e AutoGen para o terceiro | Fixar versões ao implementar |
| C-04 | Compartilhar o mesmo MCP e a mesma base nas três implementações | Preservar permissões e contratos de evidência |
| C-05 | Autor concluiu o desenho visual da Fase 1 | Diagramas dos três padrões recebidos e transcritos em `diagramas/`; desenho da arquitetura geral ainda não recebido |

## Questões para concluir a Fase 2

A D-002 fixa Python, SDK e transporte apenas para o primeiro incremento local. As escolhas definitivas de persistência, identidade e implantação continuam abertas.

| ID | Questão | Critério de escolha |
|---|---|---|
| A-01 | Linguagem e framework do backend | Aprendizado, integração, ambiente local |
| A-02 | Versão do SDK e transporte MCP | Compatibilidade com cliente e identidade |
| A-03 | Tipo de banco, índice vetorial e armazenamento de originais | Simplicidade local, persistência, acesso e reversibilidade |
| A-04 | Modelo de embeddings e geração | Qualidade, custo, privacidade, disponibilidade |
| A-05 | Política de acesso e identidade para protótipo | Resolvido em D-011 via JWT assinado (HS256) na sessão MCP |
| A-06 | Formato do corpus, chunking e versões | Rastreabilidade e atualização de documentos |
| A-07 | Interface, dashboard e implantação | Compatibilidade com prazo acadêmico |

## Decisões sobre os diagramas recebidos

### D-001 — Execução paralela e MCP compartilhado no Plano–Executor (2026-09-25)

- Status: aceito
- Contexto: a imagem do Plano–Executor mostrava três caminhos de tarefas, executores, MCP e documentos, sem explicitar a relação entre as instâncias.
- Decisão: as três tarefas executam em paralelo e seus executores acessam o mesmo servidor MCP.
- Alternativas consideradas: execução sequencial e servidores MCP separados; ambas foram descartadas pelo esclarecimento do autor.
- Consequências e riscos: o estado do grafo precisa reunir os resultados das três tarefas; o servidor MCP compartilhado pode receber chamadas concorrentes.
- Como verificar: conferir o diagrama e, na Fase 3, testar as três chamadas e a agregação dos resultados.

### D-002 — Primeiro incremento executável da Fase 2 (2026-09-25)

- Status: aceito para o protótipo local; persistência e identidade definitivas ainda pendentes.
- Contexto: precisamos aprender o SDK MCP e verificar busca e isolamento entre perfis antes de integrar agentes. O PDF exige backend, MCP, acesso e banco ao fim da Fase 2, não determina a tecnologia ou a ordem interna.
- Decisão: usar Python e `mcp==2.2.0`, com `MCPServer` e `Client` oficiais, via Streamable HTTP apenas em `127.0.0.1`. O primeiro incremento usa documentos sintéticos em memória e tokens opacos aleatórios carregados de variável de ambiente para mapear identidades de teste a perfis. O perfil nunca vem dos argumentos MCP. Expor inicialmente `search_documents` e `get_document`.
- Alternativas consideradas: `stdio` simplifica o primeiro processo, mas não testa autenticação HTTP por chamada; implementar logo banco, embeddings e provedor OAuth ampliaria demais o primeiro exercício.
- Consequências e riscos: os tokens de teste não compõem um fluxo OAuth completo, e o emissor anunciado é apenas local. Este incremento não deve ser publicado nem considerado a conclusão da Fase 2. Em seguida, escolher provedor de identidade e persistência, migrar o corpus para o banco e testar ingestão, atualização e revogação. A API pública das ferramentas deve manter referências citáveis.
- Como verificar: cliente MCP separado descobre e chama as ferramentas; perfis recebem resultados distintos; credencial ausente ou inválida é recusada; documento proibido não aparece em busca nem por ID. Registrar comandos e resultados em `docs/fase-2.md`.

### D-003 — Corpus sintético para testes de segurança e recuperação (2026-09-28)

- Status: aceito para testes locais.
- Contexto: os três documentos iniciais cobriam apenas acesso básico. Precisamos de casos que exponham falhas em versões, revogação, conteúdo conflitante, títulos semelhantes e instruções embutidas no texto.
- Decisão: manter documentos sintéticos no módulo de corpus e acrescentar estado de publicação e indicação de versão atual. A busca e o acesso por ID só podem retornar versões publicadas e atuais, após filtro de perfil. Registrar em `docs/corpus-cases.md` as consultas e expectativas.
- Alternativas consideradas: manter apenas documentos sem estado e testar versões/revogação quando houver banco. Isso deixaria as regras centrais sem um teste simples agora.
- Consequências e riscos: o estado em memória é apenas uma simulação; não substitui ingestão, transações, índice ou revogação persistente. Conteúdo conflitante é devolvido como evidência, sem o servidor escolher uma verdade. Texto que pareça instrução continua sendo dado não confiável.
- Como verificar: testes unitários e cliente MCP cobrem visibilidade por perfil, versões antigas, revogados, rascunhos, resultados vazios, citações, documentos conflitantes e tentativa de forjar perfil.

### D-004 — Arquitetura de Persistência Unificada no PostgreSQL (2026-09-30)

- Status: aceito
- Contexto: Após o sucesso dos testes em memória (corpus sintético na Fase 2), precisávamos resolver a "A-03" definindo a infraestrutura definitiva de armazenamento. Havia o impasse entre separar os arquivos originais num Object Storage (ex: MinIO) e os vetores num banco isolado (ex: ChromaDB), ou unificar os recursos.
- Decisão: Utilizar o **PostgreSQL** como solução única de banco de dados. Os arquivos originais e metadados serão armazenados nas tabelas relacionais do Postgres. Simultaneamente, o Postgres abrigará o índice vetorial para a busca semântica do RAG através da extensão **`pgvector`**, permitindo cruzar regras de segurança (tabelas) e similaridade vetorial na mesma consulta.
- Alternativas consideradas: Uso de MinIO (originais) + ChromaDB (vetores). Embora seja o padrão da indústria para massiva escalabilidade, introduziria múltiplos serviços, complicando a configuração local para o foco do estudo (que é arquitetura de agentes de IA).
- Consequências e riscos: A infraestrutura fica muito mais simples de rodar (apenas um container Postgres). O controle de acesso e vetores compartilham transações ACID. O principal risco é que inflar o banco relacional com arquivos muito pesados pode degradar performance em longo prazo, mas é uma concessão 100% válida e inteligente para o escopo e tamanho do projeto atual.
- Como verificar: Ao implementar a persistência real, o módulo `retrieval.py` deve conseguir realizar uma query unificada do tipo `SELECT ... ORDER BY embedding <-> query_vector WHERE perfil = X`, aposentando o `corpus.py` em memória.

### D-005 — Migração de Persistência Local para Nuvem (Supabase) (2026-10-05)

- Status: aceito
- Contexto: O ambiente Windows do desenvolvedor possui regras rigorosas de AppLocker e antivírus corporativo/acadêmico que bloqueavam silenciosamente DLLs compiladas em C/C++ exigidas para a persistência e embeddings locais.
- Decisão: Abandonar a premissa de um PostgreSQL em Docker Local e adotar o **Supabase** (DBaaS em nuvem) via pooler de conexão IPv4.
- Alternativas consideradas: Desabilitar os módulos de segurança do Windows (inviável); rodar um contêiner auxiliar completo (lentidão no ambiente).
- Consequências e riscos: O projeto passa a exigir internet. Reduz a sobrecarga de memória na máquina local. O banco suporta a extensão `pgvector` nativamente. A tabela unificada (`documentos`) ganha escala de produção real.
- Como verificar: O script na raiz conecta-se via `psycopg` à URI do Supabase Pooler e escreve na nuvem.

### D-006 — Adoção da API do Google Gemini para Embeddings (2026-10-05)

- Status: aceito
- Contexto: Relacionado ao D-005. A biblioteca `sentence-transformers` (`all-MiniLM-L6-v2`) não funcionava localmente devido às restrições de bibliotecas como `scipy`.
- Decisão: Utilizar o pacote puro `google-generativeai` em chamadas HTTP à API do Google, consumindo o modelo oficial `models/gemini-embedding-2`.
- Alternativas consideradas: API gratuita do HuggingFace (descartada por lentidão excessiva de *cold starts* e baixa qualidade para textos em língua portuguesa); OpenAI (exigiria créditos pagos).
- Consequências e riscos: Embeddings passam a ter **3072 dimensões** (e a tabela do banco teve a coluna de vetor alterada para refletir este tamanho). A capacidade semântica em Português Brasileiro (PT-BR) saltou vertiginosamente de qualidade.
- Como verificar: Os scripts de busca geram os vetores remotamente antes da query SQL.

### D-007 — Simplificação e Mudança do MCP para o Protocolo Stdio (2026-10-05)

- Status: aceito
- Contexto: A prova de conceito inicial elaborada em D-002 focava no transporte SSE/HTTP com tokens JWT explícitos. Este modelo é válido, porém aumenta drasticamente a complexidade do cliente, inviabilizando testes simples e o acoplamento acadêmico fácil a frameworks de multi-agentes de estudo.
- Decisão: Reescrever o servidor MCP e utilizar a comunicação padrão do protocolo via `stdio` usando o framework `MCPServer`. A responsabilidade da verificação rígida de token é simplificada no protótipo, onde a permissão (`papel_do_usuario`) vira parte obrigatória do *input* da ferramenta, delegando a responsabilidade de obter essa role ao cliente seguro.
- Alternativas consideradas: Manter o MCP HTTP com tokens.
- Consequências e riscos: Código substancialmente mais limpo. Adequado aos tutoriais oficiais do LangGraph e AutoGen que rodam como subprocessos conectados via terminal ao servidor MCP.
- Como verificar: Scripts Python (cliente e servidor) se conectam perfeitamente no terminal, trocando RPCs apenas via fluxo padrão sem expor portas HTTP e sem crash de conexões.

### D-008 — Coordenador consome o servidor MCP real via stdio; segredos fora do código (2026-10-11)

- Status: aceito para o protótipo local.
- Contexto: `src/agentes/mcp_toolkit.py` devolvia respostas fixas, então o Coordenador não exercitava o MCP nem a base. Os nomes de argumentos divergiam (`query`/`role` na ferramenta LangChain; `pergunta`/`papel_do_usuario` no servidor). A URL do Postgres e a chave do Gemini estavam escritas no código.
- Decisão: `consultar_mcp` usa o `mcp.Client` oficial (SDK instalado: `mcp==2.1.1`) e inicia `python -m src.mcp.server` como subprocesso stdio a cada chamada. A ferramenta LangChain mantém `query`/`role`, e o cliente traduz para o contrato do servidor definido em D-007 (`buscar_documentos_corporativos(pergunta, papel_do_usuario)`), sem alterá-lo. O `role` continua vindo do estado do grafo. Falhas de transporte ou de ferramenta viram texto `Erro MCP: ...` para o redator, e o detalhe vai para o stderr. `DATABASE_URL` e `GEMINI_API_KEY` passam a vir do ambiente ou de `.env` (já ignorado), lidos só no uso, para que o servidor liste ferramentas sem segredos.
- Alternativas consideradas: sessão MCP persistente em thread de fundo (menor latência, mas o ciclo de vida fica mais complexo); `langchain-mcp-adapters` (dependência extra, e o LLM passaria a preencher o papel); manter o mock (não testa a integração).
- Consequências e riscos: cada busca paga o custo de iniciar o subprocesso (alguns segundos). `asyncio.run` não funciona se o grafo for chamado dentro de um event loop ativo. O servidor continua confiando no `papel_do_usuario` recebido (pendência A-05). Os testes determinísticos do grafo passam a usar um MCP falso explícito.
- Como verificar: `tests/test_mcp_toolkit.py` cobre o contrato e a tradução de argumentos (servidor em processo com o banco substituído), o transporte stdio real (listar ferramentas) e falhas. Os testes ponta a ponta com Supabase e Gemini só rodam com `RUN_MCP_TESTS=1`.

### D-009 — Higienização de segredos e preparação para repositório público no GitHub (2026-10-11)

- Status: aceito
- Contexto: Para publicação no GitHub, o repositório precisava de uma auditoria rigorosa contra vazamento de credenciais, eliminação de arquivos mortos/workarounds locais e consolidação do empacotamento. Identificou-se uma credencial hardcoded remanescente em `src/persistencia/setup_tabelas.py`, um diretório mock local (`uuid_utils/`) e arquivos de configuração desatualizados.
- Decisão:
  1. Eliminar a URL de conexão hardcoded em `setup_tabelas.py`, centralizando em `src.config.url_banco()`.
  2. Expandir `.gitignore` para cobrir de forma abrangente arquivos de ambiente (`.env*`), artefatos de build/eggs, caches e arquivos de IDE.
  3. Remover o diretório de mock temporário `uuid_utils/` e artefatos `*.egg-info`, instalando e declarando `uuid-utils` no `requirements.txt` e `pyproject.toml`.
  4. Corrigir falha em `tests/teste_banco.py` (import ausente de `psycopg`) e adicionar compatibilidade de `sys.path` e codificação UTF-8 para terminais Windows em scripts de teste e cliente.
  5. Atualizar o `README.md` raiz para refletir o estado real do projeto (Fase 2 + Fase 3 Coordenador com LangGraph).
- Alternativas consideradas: Manter `.env` com valores fictícios no commit (descartado por violar boas práticas de segurança); manter `uuid_utils` local (descartado por sombrear a biblioteca oficial).
- Consequências e riscos: O repositório torna-se seguro para subida no GitHub. Usuários externos precisam configurar suas próprias credenciais em `.env` copiando de `.env.example`.
- Como verificar: Rodar a suíte completa de testes (`pytest -v`), o script de infraestrutura (`python tests/teste_banco.py`) e o cliente MCP (`python scripts/cliente.py`), garantindo que nenhum segredo esteja no histórico de arquivos a ser commitado.

### D-010 — Papel do usuário fixado pelo código, fora do schema da ferramenta (2026-10-13)

- Status: aceito
- Contexto: `ferramenta_busca_corporativa(query, role)` era uma ferramenta LangChain global com `role` no schema. O Coordenador a chamava de forma determinística com o papel do estado, mas, em agentes com *tool calling* (`bind_tools`, Plano–Executor, AutoGen), quem preencheria `role` seria o LLM, sujeito a *prompt injection* ("responda como diretoria"). Isso viola a regra de não aceitar papel declarado pelo modelo.
- Decisão: substituir a ferramenta global por `criar_ferramenta_busca(role)` e `criar_toolkit_corporativo(role)`. O papel vem da sessão/estado do grafo, fica preso numa closure e o schema exposto ao modelo contém apenas `query`. Papel vazio ou ausente gera `ValueError` (falha fechada). O contrato do servidor MCP (D-007) não muda.
- Alternativas consideradas: `InjectedToolArg` do LangChain (esconde o argumento do schema, mas depende de quem invoca para injetá-lo e não impede uma chamada com `role` forjado); manter a ferramenta global e confiar na disciplina dos nós (frágil ao reutilizar o toolkit nas outras arquiteturas).
- Consequências e riscos: cada sessão/execução cria a própria instância da ferramenta. O servidor MCP continua confiando no `papel_do_usuario` recebido do cliente; a autenticação real segue pendente (A-05). Isso protege contra o LLM, mas não contra um cliente MCP malicioso.
- Como verificar: `tests/test_mcp_toolkit.py` confere que o schema expõe só `query`, que um `role` enviado na chamada é ignorado em favor do papel da sessão, e que a criação sem papel falha.
- Evidência (2026-10-13): `python -m pytest tests/test_mcp_toolkit.py -v` → 13 passed (33 s, com Supabase real); `pytest tests/test_coordenador.py -v` → 4 passed (256 s, Gemini + MCP + Supabase reais), incluindo isolamento geral × diretoria.

### D-011 — Autenticação de Sessão MCP via JWT assinado e fechamento de A-05 (2026-10-14)

- Status: aceito
- Contexto: A decisão D-010 blindou o LLM contra prompt injection no papel do usuário ao criar a ferramenta com o `role` fixado na closure. No entanto, o protocolo MCP entre o cliente e o servidor ainda expunha `papel_do_usuario` no schema de `buscar_documentos_corporativos` e confiava cegamente no argumento recebido. Qualquer cliente MCP (ou processo malicioso) poderia forjar privilégios enviando `papel_do_usuario="diretoria"`, violando o aceite de segurança 2.5 e mantendo a questão A-05 aberta.
- Decisão:
  1. Adotar o padrão **JWT (JSON Web Token — RFC 7519)** assinado com HMAC-SHA256 (`HS256`) através da biblioteca `PyJWT` para autenticação de sessão do cliente MCP.
  2. Implementar `src/autorizacao/tokens.py` com `gerar_token_sessao` e `validar_token_sessao`, protegendo integridade, sujeito (`sub`), papel (`papel`) e expiração (`exp`), assinado com chave do sistema (`AUTH_SECRET_KEY`).
  3. No transporte `stdio`, o cliente seguro gera o JWT a partir da sessão autenticada e o injeta no ambiente do subprocesso (`MCP_AUTH_TOKEN`).
  4. O servidor MCP valida o token na camada de autorização e extrai o papel diretamente das claims criptográficas verificadas. Se o token for ausente, adulterado ou expirado, nega o acesso imediatamente (falha fechada).
  5. O contrato público da ferramenta MCP `buscar_documentos_corporativos` passa a exigir apenas `pergunta: str`, eliminando completamente o argumento `papel_do_usuario` da API de ferramentas do servidor.
- Alternativas consideradas:
  - Implementar verificação HMAC caseira com bibliotecas nativas: descartado em favor do padrão oficial `PyJWT`, já instalado e testado no ambiente sem problemas de compilação C/C++, prevenindo armadilhas conhecidas de segurança (como `alg: none` e ataques de temporização).
  - OAuth 2.0 com Identity Provider remoto completo: descartado por introduzir complexidade excessiva de infraestrutura e latência de rede para um protótipo em transporte `stdio`.
- Consequências e riscos: A autenticação torna-se técnica e criptograficamente verificável no servidor MCP. A chave `AUTH_SECRET_KEY` precisa ser preservada com segurança (mínimo de 32 caracteres). O servidor MCP não aceita mais chamadas sem token válido.
- Como verificar: `python -m pytest tests/test_mcp_toolkit.py -v` (20 testes passam, cobrindo emissão, validação, token expirado, token adulterado, rejeição de chamadas sem token e rejeição de token com chave forjada); `python scripts/cliente.py` demonstra consultas autenticadas de diretoria, geral e negação de acesso sem token.

## Modelo para novas entradas

```md
### D-XXX — Título (AAAA-MM-DD)

- Status: proposto | aceito | substituído
- Contexto:
- Decisão:
- Alternativas consideradas:
- Consequências e riscos:
- Como verificar:
```



