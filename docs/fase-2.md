# Plano de execução — Fase 2

**Objetivo:** construir backend e integração segura via MCP, demonstrados por chamadas de cliente MCP sem agentes. Os passos são uma proposta incremental, não uma imposição literal do cronograma acadêmico.

## 2.1 Fixar um recorte técnico

Escolher linguagem/backend, SDK MCP e versão, transporte, persistência, embeddings, corpus de exemplo e mecanismo de identidade. Escrever uma decisão em `decisions.md` com alternativas e modo local de execução. Priorizar componentes simples e substituíveis.

**Aceite:** outra pessoa consegue repetir a preparação do ambiente; nenhuma credencial no código.

## 2.2 Corpus e esquema

Criar documentos sintéticos com versões e acessos diferentes. Definir IDs de documento/versão/trecho, metadados, papéis, permissões e referências citáveis. Não usar informações privadas reais no exemplo.

**Aceite:** matriz esperada de acesso e origem de cada trecho está documentada.

## 2.3 Pipeline de ingestão e recuperação

Armazenar fonte, extrair, dividir, indexar e consultar; suportar atualização e revogação. Instrumentar falhas e latência. Inicialmente, recuperação textual simples pode servir de linha de base; documentar quando e por que embeddings forem incorporados.

**Aceite:** pergunta conhecida recupera sua fonte, pergunta sem resposta retorna vazio, revogação retira o conteúdo pesquisável e falha parcial não publica versão inconsistente.

## 2.4 Servidor MCP

Expor inicialmente busca e acesso por ID; acrescentar metadados/listagem quando seus filtros e permissões estiverem prontos. Usar contratos em `mcp.md`, fixar versão do SDK e provar invocação com cliente MCP.

**Aceite:** descoberta e chamadas reais funcionam; erros e limites são previsíveis; nenhum agente é necessário.

## 2.5 Segurança

Estabelecer identidade confiável e autorização no servidor para cada rota, metadado e resultado. Aplicar negação por padrão, validar entrada e auditar sem conteúdo sensível. A implementação de OAuth depende do transporte escolhido e não deve ser simulada com papéis escolhidos pelo chamador.

**Aceite:** testes mostram permissões distintas e ausência de vazamento por busca, listagem, ID e versões antigas.

## 2.6 Demonstração e revisão

Preparar comandos reproduzíveis para subir infraestrutura, ingerir corpus, iniciar servidor, rodar cliente e executar testes. Registrar limite conhecido, evidência de testes e requisitos para passar à Fase 3.

**Conclusão da fase:** consulta MCP autorizada retorna trechos com origem; consultas proibidas são negadas; atualização/revogação funciona; testes e instruções reproduzem o resultado. Depois implementar padrões um por vez com este contrato congelado ou versionado.

## Plano de implementação em incrementos

Este plano detalha a Fase 2 do PDF. O PDF exige backend, servidor MCP, políticas de acesso e integração com banco; corpus sintético, divisão em trechos, ferramentas específicas e testes com cliente MCP são decisões de estudo para tornar essa exigência verificável. As tecnologias abaixo continuam **pendentes de decisão**, conforme `decisions.md`. Não iniciar a Fase 3 para validar a Fase 2.

| Ordem | Incremento e entrega revisável | Verificação para avançar |
|---|---|---|
| 0 | Registrar em `decisions.md` a linguagem, SDK e versões fixadas, transporte, persistência, forma de busca, identidade confiável e modo local de execução. Conferir o diagrama geral da Fase 1 quando estiver disponível. | Ambiente reproduzível e fronteira de confiança descrita; nenhum papel declarado em argumento de ferramenta concede acesso. |
| 1 | Criar corpus **sintético** pequeno, esquema de documento/versão/trecho e matriz documento × perfil; definir perguntas conhecidas, sem resposta e proibidas. | Cada trecho tem ID e origem estáveis; expectativas de acesso estão escritas antes da implementação. |
| 2 | Implementar ingestão administrativa e persistência em módulos próprios: salvar original, metadados, checksum, estado e trechos; publicar somente versão completa. | Reingestão idempotente, falha parcial não publica versão e versão revogada deixa de ser consultável. |
| 3 | Implementar recuperação textual inicial, com interface separada para trocar ou complementar o mecanismo de busca depois. Consultar somente versões publicadas e elegíveis. | Pergunta conhecida retorna fonte esperada; pergunta sem evidência retorna vazio; atualização não mistura versões. |
| 4 | Implementar autorização centralizada por identidade confiável, com negação por padrão, antes de expor resultados ou metadados. Registrar decisão de acesso e tempo sem copiar conteúdo aos logs. | Testes de perfis distintos cobrem busca, ID, metadados e versões; inexistente e proibido não revelam dados indevidos. |
| 5 | Expor `search_documents` e `get_document` no servidor MCP. Fechar tipos, limites, paginação e erros conforme SDK escolhido; acrescentar `get_document_metadata` e `list_documents` somente após terem filtros e testes completos. | Cliente MCP real descobre e chama as ferramentas; saídas trazem referência citável; entradas inválidas e limites têm comportamento previsível. |
| 6 | Publicar um roteiro de demonstração local, testes automatizados e registro de resultados com comando, ambiente, data e evidência. | Outra pessoa consegue preparar o ambiente, ingerir, iniciar servidor, executar cliente e reproduzir casos positivos, vazios e negados. |

### Contratos a fechar no incremento 0

- **Identidade e transporte:** decidir juntos. Em `stdio`, explicitar quem inicia o processo e como a identidade autenticada chega ao servidor; em HTTP, definir verificação de credenciais apropriada ao transporte. Um `role` enviado pelo modelo ou pelo próprio argumento da ferramenta nunca é prova de identidade.
- **Modelo de dados:** `document_id` estável; `version_id` imutável; `chunk_id` único por versão; estado `staged`, `published` ou `revoked`; classificação e permissões consultadas da fonte de verdade. Citação deve reconstruir documento, versão e posição do trecho.
- **Resposta MCP:** fixar campos, tamanho máximo de trecho, limites de consulta, semântica de resultado vazio e erros antes de integrar agentes. Evitar título, contagem ou mensagem de erro que revele documento inacessível.
- **Busca:** começar com método determinístico local, se ele satisfizer o corpus de teste. Introduzir embeddings apenas com justificativa e teste de regressão; manter a mesma interface de recuperação e autorização.

### Matriz mínima de testes de aceitação

| Caso | Resultado esperado |
|---|---|
| Perfil autorizado busca assunto conhecido e acessa o ID retornado | Trecho correto com `document_id`, `version_id`, `chunk_id` e citação. |
| Perfil diferente busca o mesmo assunto, lista ou pede metadados/ID | Só vê conteúdo permitido; documento proibido não aparece nem vaza em erro. |
| Perfil sem permissão ou identidade ausente | Acesso negado por padrão em toda ferramenta. |
| Consulta sem resposta no corpus | Lista vazia, sem fonte inventada. |
| Documento atualizado ou revogado | Versão antiga não aparece em busca nem é acessível por ID. |
| Extração ou indexação falha | Versão incompleta não é publicada; falha auditável. |
| Entrada inválida, limite excessivo ou ID malformado | Erro estável, sem conteúdo interno ou sensível. |
| Cliente MCP independente | Descobre capacidades e executa os mesmos casos sem agentes. |

**Marco de saída:** registrar no repositório os comandos e resultados desses testes, as versões efetivamente usadas, limites conhecidos e o contrato MCP congelado ou versionado para a Fase 3. A fase permanece aberta enquanto qualquer caso essencial da matriz falhar.

## Evidência do primeiro incremento (2026-09-25)

- Ambiente usado: Windows, Python 3.12.14 em `.venv`, SDK `mcp==2.2.0`, cliente e servidor negociando protocolo `2026-07-28`, transporte Streamable HTTP em `127.0.0.1`.
- Instalação: `.venv\Scripts\python.exe -m pip install -e .` — concluída.
- Testes: `.venv\Scripts\python.exe -m unittest discover -s tests -v` — 3 testes passaram (isolamento, busca vazia/citação e limite inválido).
- Demonstração: `.venv\Scripts\python.exe -m phase2.demo` — `DEMO OK`; descobriu `search_documents` e `get_document`; RH encontrou `doc-rh-001:v1:c1`, Engenharia encontrou `doc-eng-001:v1:c1`; perfil externo não recebeu o documento de RH nem na busca nem por ID; ausência de token e token inválido retornaram HTTP 401. Uma consulta sem evidência retornou lista vazia.
- Limites: corpus em memória, busca textual simples, tokens de teste sem provedor OAuth, sem banco, ingestão, atualização/revogação ou interface. Os critérios integrais da Fase 2 continuam abertos.

## Ampliação do corpus (2026-09-28)

O corpus sintético e os testes foram ampliados conforme `docs/corpus-cases.md`: versões antiga/atual, revogado, rascunho, documento compartilhado, exclusivo de externo, títulos iguais com permissões distintas, evidências conflitantes, texto hostil e acentuação. Busca e acesso por ID agora exigem estado `published` e versão atual. Isso simula visibilidade de versões; não implementa ingestão ou revogação persistente.

**Validação pendente:** o terminal da sessão falhou com `helper_unknown_error: setup refresh had errors`, então os novos testes e a demonstração ampliada ainda precisam ser executados. Comandos: `.venv\Scripts\python.exe -m unittest discover -s tests -v` e `.venv\Scripts\python.exe -m phase2.demo`. Não considerar os novos casos aprovados até registrar suas saídas.

## Cliente MCP real no Coordenador (2026-10-11, D-008)

- Ambiente: Windows, Python 3.14.6 global, `mcp==2.1.1` instalado (o `pyproject.toml` ainda declara 2.2.0), `langgraph==1.2.14`, `psycopg==3.3.6`, Supabase + `gemini-embedding-2`.
- Preparação: copiar `.env.example` para `.env` e preencher `DATABASE_URL` e `GEMINI_API_KEY`. O servidor roda com `python -m src.mcp.server`, a partir da raiz.
- Testes determinísticos: `python -m pytest tests/test_mcp_toolkit.py tests/test_coordenador.py -v` — 14 passaram e 6 foram pulados (testes reais opcionais). Cobrem: contrato da ferramenta, tradução `query/role` → `pergunta/papel_do_usuario`, isolamento com banco falso, resultado vazio, erro na ferramenta sem vazar detalhe, servidor que não sobe, listagem via stdio real sem segredos e repasse restrito de variáveis ao subprocesso.
- Ponta a ponta: `$env:RUN_MCP_TESTS="1"; python -m pytest tests/test_mcp_toolkit.py -v` — 12 passaram. Diretoria recebeu o orçamento (2027); `geral` não recebeu o orçamento nem a senha do RH.
- Ainda não executado: testes com o LLM real atravessando o MCP real (`$env:RUN_LLM_TESTS="1"; python -m pytest tests/test_coordenador.py -v`).
- Limites: o papel ainda chega como argumento da ferramenta (A-05 aberto, contraria o aceite 2.5); a resposta não tem `document_id`/citação; não há atualização/revogação; um subprocesso é iniciado por chamada.

