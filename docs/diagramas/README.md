# Diagramas da Fase 1

Coloque aqui os fluxos visuais já produzidos para Coordenador, Plano–Executor, Conversação em Grupo e arquitetura geral. Para cada desenho, registre data, versão e decisões que o desenho representa. Revise `../architecture.md` e `../multi-agent.md` quando surgirem divergências; não presuma que os esboços textuais deste pacote reproduzem os diagramas ausentes.

## Diagramas recebidos

| Padrão | Arquivo | Registro | Decisões representadas |
|---|---|---|---|
| Coordenador | [coordenador.mmd](coordenador.mmd) | 2026-09-25, versão 1; transcrição da imagem enviada pelo autor | Usuário → Coordenador; Coordenador, Retrieval Agent, Analyst Agent e Validator Agent dentro do LangGraph; apenas Retrieval Agent se conecta ao servidor MCP, que acessa documentos corporativos. |
| Plano–Executor | [plano-executor.mmd](plano-executor.mmd) | 2026-09-25, versão 2; imagem do autor e esclarecimento posterior | Usuário → Planner; três tarefas executadas em paralelo por três executores dentro do LangGraph; todos acessam os mesmos documentos pelo mesmo servidor MCP. |
| Conversação em Grupo | [conversacao-em-grupo.mmd](conversacao-em-grupo.mmd) | 2026-09-25, versão 1; transcrição da imagem enviada pelo autor | Usuário → Group Chat dentro do AutoGen; Group Chat ligado a Retrieval, Analyst e Validator; apenas Retrieval segue para MCP → Documents. |

O desenho do Coordenador representa componentes e conexões, sem definir ordem de execução, condições de roteamento ou fluxo de retorno. Esses detalhes seguem em aberto para a implementação da Fase 3. A ligação entre Retrieval Agent e servidor MCP deve usar um cliente MCP, conforme a fronteira descrita em `../architecture.md`; o cliente não está desenhado na imagem original.

O autor esclareceu que as três tarefas executam em paralelo e que as três caixas MCP da imagem representam o mesmo servidor. A versão 2 reúne esses caminhos em um único nó MCP. Cada executor deve usar um cliente MCP para consultar documentos, conforme `../architecture.md`; esses clientes não estão desenhados na imagem original.

O desenho da Conversação em Grupo identifica papéis e conexões, mas não define a ordem das falas, o critério de seleção do próximo agente ou a condição de término. A ligação entre Retrieval e MCP deve usar um cliente MCP, conforme `../architecture.md`; esse cliente não está desenhado na imagem original.
