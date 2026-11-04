# Observabilidade, avaliação e resiliência

## Instrumentação desde a Fase 2

Gerar um `run_id` por pergunta e ligar chamada da interface, execução do padrão, chamada MCP, busca e resposta. Guardar versão do corpus, configuração, horário, resultado, tempo e erro. Dados de usuário, trechos e prompts exigem minimização e política de retenção; métricas podem ser coletadas sem copiar conteúdo sensível para logs.

## Métricas para a Fase 4

| Medida | Definição operacional inicial |
|---|---|
| Latência | Tempo até resposta final e tempo por etapa; percentis sobre várias execuções |
| Tokens | Entrada e saída por chamada e total; registrar indisponibilidade quando provedor não informa |
| Custo | Estimativa por modelo/tabela de preços versionada, com moeda e data |
| Chamadas MCP | Total por ferramenta, erros, negações e retries |
| Recuperação | Cobertura da evidência esperada, documentos irrelevantes e acesso negado corretamente |
| Fidelidade | Afirmações relevantes sustentadas por trechos citados, com rubrica de revisão |
| Resposta | Correção, completude e capacidade de dizer “não sei” sem evidência |
| Segurança | Tentativas de acesso indevido bloqueadas em busca, metadados e documento |

Não use “score de similaridade = 0,92” como probabilidade de acerto, nem reduza alucinação a uma única porcentagem sem definir critério e amostra. Para comparar custos, registre versões e preços da época do experimento.

## Conjunto de avaliação

Criar perguntas com respostas e trechos de referência, perguntas ambíguas, respostas inexistentes, documentos conflitantes, diferentes perfis e tentativas de instruções maliciosas dentro do texto recuperado. Fixar corpus e perguntas antes de rodar os padrões; reportar quantidade, método de julgamento e incerteza. Executar mais de uma vez quando a geração não for determinística.

## Falhas a ensaiar

Timeout do servidor MCP, documento removido após indexação, erro de embedding, índice indisponível, token de acesso inválido, resultado vazio e limite de iterações. A resposta deve falhar de modo explícito e auditável, evitando inventar fontes.

## Dashboard e relatório

Exibir série temporal, percentis de latência, custo estimado, chamadas MCP/LLM, erros e qualidade por padrão. O relatório da Fase 5 deve incluir o método de medição, tabelas comparáveis, exemplos anonimizados, gargalos, limites e propostas de melhoria. A interface de perguntas é outro objetivo do planejamento e terá escopo próprio.

---

## Implementação Concluída na Fase 4

1. **Camada de Telemetria e FinOps (`src/observabilidade/`)**:
   - `telemetria.py`: persistência local de `execucoes`, `spans` e `avaliacoes` no SQLite (`data/telemetria.db`). Rastreamento via `ContextVar` compatível com LangGraph e AutoGen 0.4.
   - `custos.py`: precificação oficial versionada do Gemini em USD e BRL.
2. **Benchmark e Golden Dataset (`data/golden_dataset.json`)**:
   - 24 perguntas balanceadas em 5 categorias (públicas, confidenciais diretoria, confidenciais RH, fora do corpus para anti-alucinação e injeção de prompt adversária).
   - Pipeline de benchmark automatizado em `scripts/executar_benchmark.py`.
3. **Avaliação Semântica (Evals) e Anti-Alucinação (`avaliador.py`)**:
   - LLM-as-a-Judge com temperatura 0 e Pydantic estruturado (`VereditoJuiz`).
   - Verificação determinística de RBAC para prevenir e auditar vazamentos de credenciais.
4. **Resiliência e Engenharia do Caos (`tests/resiliencia/`)**:
   - 10 testes automatizados cobrindo transporte MCP, tokens forjados/expirados, queda de banco PostgreSQL e injeção de prompt direta/indireta.
5. **Interface de Usuário e Dashboard (`src/ui/app.py`)**:
   - Aplicação unificada em Streamlit com aba de Chat interativo e aba de Dashboard analítico com gráficos comparativos em Plotly.

