# Relatório de Implementação e Decisões: Persistência e Dados (Fase 2)

## 1. Contexto e Objetivo
Este documento detalha as implementações técnicas e arquiteturais realizadas para suprir a primeira etapa da **Fase 2** do Estudo Dirigido: *"implementação mínima verificável de dados, recuperação e controle de acesso"*. O objetivo foi estabelecer uma base sólida de conhecimento (banco de dados vetorial) que será posteriormente consumida pelos agentes através de um servidor MCP.

## 2. Desvios de Planejamento e Decisões Arquiteturais
Durante a implementação, enfrentamos restrições rigorosas do sistema operacional (Windows) via AppLocker/Políticas de Controle de Aplicativo, que bloqueavam a execução de bibliotecas C/C++ compiladas (`.pyd` / DLLs) não assinadas. Isso nos forçou a pivotar a arquitetura local para uma arquitetura em nuvem.

### Decisão 1: Migração do Docker Local para Supabase (DBaaS)
- **Contexto original:** O plano era rodar um contêiner PostgreSQL (`pgvector/pgvector:pg15`) localmente via `docker-compose`.
- **Problema:** A restrição de segurança da máquina impediria a execução eficiente dos scripts Python locais que interagiriam com o banco.
- **Decisão:** Adotar o **Supabase** como provedor de banco de dados em nuvem.
- **Efeito:** O projeto ganhou um banco de dados PostgreSQL com `pgvector` nativo, altamente disponível (IPv4 via Transaction Pooler), sem consumo de memória local e que abre portas para uso futuro do Supabase Auth e Storage (alinhado com os requisitos do projeto).

### Decisão 2: Substituição do modelo Local (Sentence-Transformers) pela API do Gemini
- **Contexto original:** Planejávamos usar o modelo `all-MiniLM-L6-v2` rodando na própria máquina para gerar os embeddings.
- **Problema:** A biblioteca dependia de pacotes como `scipy` e `torch`, cujas DLLs foram barradas pelo antivírus corporativo/acadêmico.
- **Decisão:** Consumir a API do **Google Gemini** (modelo `models/gemini-embedding-2`).
- **Efeito:** Resolução total dos erros de segurança (a comunicação ocorre via HTTP REST puro), ganho absurdo na qualidade de compreensão semântica para a língua portuguesa e vetores mais ricos (3072 dimensões).

## 3. Estrutura do Banco de Dados
A persistência foi modelada para ser simples, porém suficiente para validar o requisito de **Controle de Acesso Seguro**.

Foi criada a tabela `documentos` com a seguinte estrutura:
- `id` (SERIAL): Identificador único.
- `conteudo` (TEXT): O corpo do documento corporativo.
- `metadados` (JSONB): Estrutura flexível para armazenar os atributos de segurança. Atualmente armazena a chave `"papel"`, definindo quem tem permissão para ler a linha (ex: `diretoria`, `geral`, `rh`).
- `embedding` (VECTOR 3072): A representação matemática do conteúdo gerada pela IA.

## 4. Testes de Aceitação Realizados
A "implementação mínima verificável" foi validada através de dois scripts:
1. **`ingestao.py`:** Salvou com sucesso documentos variados no banco, calculando os vetores na nuvem e persistindo no Supabase.
2. **`recuperacao.py`:** Validou a **Busca Semântica + Controle de Acesso (RBAC)** em uma única query SQL.
   - *Resultado do Teste:* Quando um usuário com papel `"geral"` buscou por "orçamento do projeto secreto", o banco filtrou a busca (`WHERE metadados->>'papel' IN ('geral', %s)`) e bloqueou o acesso ao documento da diretoria, retornando o conteúdo público mais próximo, provando a eficácia do isolamento de dados.

---

## 5. Próximos Passos (Roadmap da Fase 2)
Agora que a base de dados, a inteligência vetorial e a segurança em nível de linha estão validadas, os próximos passos do projeto são:

1. **Encapsulamento em Servidor MCP:**
   - Transformar a lógica do script `recuperacao.py` em uma ferramenta (tool) oficial dentro de um **Servidor MCP** (`server.py`).
   - O servidor MCP será a única porta de entrada para a leitura dos documentos.

2. **Teste com Cliente MCP:**
   - Construir (ou utilizar) um cliente MCP simples apenas para validar o contrato de entrada (pergunta e papel do usuário) e saída (resposta em texto) do servidor, garantindo que a comunicação MCP está sólida *antes* de inserir os agentes.

3. **Avanço para Fases Subsequentes (Múltiplos Agentes):**
   - Iniciar os estudos práticos com LangGraph (Coordenador / Plano-Executor) e AutoGen.
   - Plugar os agentes como clientes do servidor MCP que acabamos de construir.
