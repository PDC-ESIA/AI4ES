# Relatório Técnico de Arquitetura de Software

## 1. Identificação das HUs

Resumo das Histórias de Usuário com responsabilidades funcionais-alvo (mapeamento breve):

- HU01 — Cadastrar produto  
  Responsabilidade: permitir criação de produto com nome, quantidade inicial e preço de custo; validações de campos obrigatórios e unicidade por nome; tornar disponível imediatamente na consulta.  
  Critérios-chave: campos obrigatórios, sem duplicidade, atualização imediata da visão de estoque.

- HU02 — Registrar entrada de mercadoria  
  Responsabilidade: lançar entradas (produto + quantidade + data); atualizar saldo; registrar histórico com data/hora/usuário.  
  Critérios-chave: seleção por lista/busca, quantidade positiva, atualização imediata, histórico com timestamp.

- HU03 — Registrar saída de produto  
  Responsabilidade: lançar saídas, validar saldo disponível (bloquear se insuficiente), atualizar saldo e histórico.  
  Critérios-chave: validação de estoque, decremento imediato, registro cronológico.

- HU04 — Ser alertado sobre estoque baixo  
  Responsabilidade: exibir alerta persistente e destacado quando saldo <= limite mínimo configurado; identificar produto e saldo atual.  
  Critérios-chave: destaque visual, persistência até reposição, identificação clara.

- HU05 — Configurar limite mínimo de estoque por produto  
  Responsabilidade: editar limite mínimo (inteiro não negativo) por produto; refletir imediatamente nos alertas.  
  Critérios-chave: validação de valor, efeito imediato.

- HU06 — Consultar saldo atual do estoque  
  Responsabilidade: listar todos os produtos com nome, saldo e limite; destacar itens abaixo do limite; ordenação por nome/quantidade.  
  Critérios-chave: listagem completa, destaque visual, ordenação.

- HU07 — Consultar histórico de movimentações  
  Responsabilidade: filtros por produto e período; exibir tipo (entrada/saída), quantidade, data, hora e usuário; ordenação cronológica decrescente padrão.  
  Critérios-chave: filtros e campos completos, ordenação padrão.

- HU08 — Exportar dados de estoque e movimentações  
  Responsabilidade: exportar CSV com todos campos relevantes; escolher diretório destino; confirmação de sucesso.  
  Critérios-chave: CSV completo, seleção de diretório, confirmação.

Relação direta com RFs e RNFs já está contemplada nas HUs acima (ver Seção 6 — Cobertura de Requisitos para rastreabilidade completa).

---

## 2. Diagramas de Arquitetura (Mermaid)

Diagrama de sequência representando o fluxo "Registrar saída de produto" (inclui autenticação, validação de saldo, persistência e emissão de alerta se necessário).

```mermaid
sequenceDiagram
    autonumber
    participant Operador as Operador (UI)
    participant AppUI as Aplicação - Interface
    participant Auth as Serviço de Autenticação
    participant MovSvc as Serviço de Movimentação
    participant ProdutoSvc as Serviço de Produto / Estoque
    participant Repo as Repositório Persistente (DB embarcado)
    participant Alerta as Gerenciador de Alertas
    participant Audit as Registro de Auditoria

    Operador->>AppUI: Inicia operação de saída (seleciona produto, qtd)
    AppUI->>Auth: Verifica sessão / credenciais
    Auth-->>AppUI: Usuário autenticado (idUser)
    AppUI->>MovSvc: Solicita registro de saída(prodId, qtd, data, idUser)
    MovSvc->>ProdutoSvc: Solicita saldo atual para validação(prodId)
    ProdutoSvc->>Repo: Consulta saldo atual(prodId)
    Repo-->>ProdutoSvc: Retorna saldo atual
    ProdutoSvc-->>MovSvc: Saldo atual (valor)
    alt qtd <= saldo
        MovSvc->>Repo: Inicia transação; grava movimento (tipo=saída, qty, timestamp, user)
        Repo-->>MovSvc: Confirma gravação de movimento
        MovSvc->>Repo: Atualiza saldo no registro de produto
        Repo-->>MovSvc: Confirma atualização de saldo
        MovSvc->>Audit: Registra entry com data/hora/usuário
        Audit-->>MovSvc: Audit confirmado
        MovSvc-->>AppUI: Sucesso (novo saldo)
        AppUI->>Operador: Exibe confirmação e novo saldo
        alt novoSaldo <= limiteMinimo
            MovSvc->>Alerta: Notificar estoque baixo(prodId, novoSaldo, limite)
            Alerta-->>AppUI: Push/Marca visual de alerta
        end
    else qtd > saldo
        MovSvc-->>AppUI: Erro: quantidade excede saldo
        AppUI->>Operador: Exibe mensagem de erro clara
    end
```

Diagrama de componentes (visão lógica dos módulos principais e interfaces):

```mermaid
graph LR
    UI[Interface Desktop (UI)]
    AUTH[Serviço de Autenticação]
    PROD[Serviço de Produto / Estoque]
    MOV[Serviço de Movimentação]
    ALERT[Gerenciador de Alertas / Notificações]
    EXPORT[Serviço de Exportação CSV]
    QUERY[Serviço de Consulta / Relatórios]
    REPO[Repositório Persistente (DB embarcado + WAL)]
    AUDIT[Registro de Auditoria (anexado ao Repo)]
    FS[Subsistema de Arquivos (diretório de exportação/backup)]

    UI-->|requisições UI|AUTH
    UI-->|UI: CRUD Produtos / Config limites|PROD
    UI-->|UI: Lançar Entrada/Saída|MOV
    UI-->|Visualizar Alertas|ALERT
    UI-->|Exportar CSV|EXPORT
    AUTH-->|valida/retorna idUser|REPO
    PROD-->|consulta/atualiza|REPO
    MOV-->|grava movimentos / atualiza saldo|REPO
    MOV-->|registra auditoria|AUDIT
    AUDIT-->|persist|REPO
    MOV-->|gera eventos|ALERT
    QUERY-->|consulta índices/relatórios|REPO
    EXPORT-->|lê dados|REPO
    EXPORT-->|escreve CSV|FS
    ALERT-->|notificações|UI
```

Observações sobre diagramas:
- "Repositório Persistente" é conceitual: representa o armazenamento local embarcado exigido (RNF02) com garantia de durabilidade/recuperação (RNF03).
- Comunicação entre componentes é interna ao processo da aplicação desktop (modelo modular), usando interfaces locais.

---

## 3. Decisões de Arquitetura

1. Arquitetura monolítica modular para aplicação desktop
   - Racional: requisito RNF01 indica aplicação desktop; solução modular facilita manutenção e implantação em ambientes sem servidor.
   - Trade-off: simplicidade de implantação vs. escalabilidade multi-cliente. Recomendado se operação for em uma única estação; se houver necessidade multi-estações, adaptar para sincronização/replicação futura.

2. Persistência local embarcada com garantia de durabilidade (conceito: base de dados embarcada + log/journal)
   - Racional: RNF02 e RNF03 exigem armazenamento local e proteção contra perda em fechamento inesperado.
   - Implementação conceitual: esquema transacional com gravação atômica de movimentações + atualização de saldo; manter um write-ahead log/journal para recuperação em caso de crash.
   - Trade-off: requer mecanismos de flush/sincronização de I/O para garantir RNF03; evita depender de servidores externos.

3. Modelo de dados transacional com tabela separada de Movimentações (append) e tabela de Produtos com saldo calculado/atualizado
   - Racional: facilita auditoria (RNF08), rendimento de consultas (RNF05) e exportação (HU08).
   - Observação: gravações de movimentações devem ser atômicas com atualização de saldo para manter consistência.

4. Garantia de consistência e validação de estoque
   - Racional: RF06/HU03 impedem saídas que excedam saldo.
   - Estratégia: validação de saldo antes de gravar; dentro de transação atômica revalidar e aplicar atualização para evitar condições de corrida (mesmo em contexto desktop considerar proteção se houver threads/paralelismo).

5. Autenticação local com armazenamento seguro das credenciais
   - Racional: RNF06 exige proteção por usuário e senha.
   - Observação: política de senhas e gerenciamento de usuários não está especificada (ver Gap Analysis).

6. UI focada em fluxo de 3 interações (RNF04)
   - Racional: Usabilidade — telas principais devem permitir operações de entrada/saída com no máximo três ações (ex.: selecionar produto → informar quantidade → confirmar).
   - Trade-off: sacrificar excesso de confirmação para velocidade; incluir undo simples ou confirmação configurável.

7. Estratégia de performance para consultas (RNF05)
   - Racional: consultas devem carregar em até 2s mesmo com grande volume.
   - Estratégias conceituais: índices em campos de filtro (nome, data), projeções limitadas para listagens, paginação incremental e cache em memória de consulta recentes/visões agregadas.

8. Exportação CSV e escolha de diretório
   - Racional: RNF07 e HU08.
   - Observação: o mecanismo de export deve streams dados do repositório para arquivo no subsistema de arquivos, com confirmação ao usuário.

9. Registro de auditoria por lançamento (RNF08)
   - Racional: toda movimentação grava: data, hora, usuário.
   - Observação: auditoria deve ser imutável (append-only) e vinculada à movimentação.

10. Alertas persistentes
    - Racional: RF09/HU04.
    - Implementação conceitual: componente de alerta que marca produtos com flag "em alerta" até que novo saldo ultrapasse limite; UI deve exibir destaque persistente.

---

## 4. Tabela de Componentes e Rastreabilidade

| Componente | Responsabilidade Principal | Comunica-se com | Origem (HU / Critério de Aceite) |
|------------|----------------------------|------------------|----------------------------------|
| Interface Desktop (UI) | Fluxos de cadastro/edição, lançamentos, consulta, exibição de alertas, exportação | AUTH, PROD, MOV, ALERT, EXPORT, QUERY | HU01, HU02, HU03, HU04, HU06, HU08; RNF04 |
| Serviço de Autenticação (AUTH) | Gerir login/sessão, validar credenciais, prover idUser para operações | UI, REPO | RNF06; RNF08 |
| Serviço de Produto / Estoque (PROD) | CRUD de produtos, configuração de limite mínimo, fornecer saldo atual | UI, REPO, MOV, ALERT | HU01, HU05, HU06; RF01, RF02, RF03, RF08 |
| Serviço de Movimentação (MOV) | Registrar entradas/saídas, validar saldo, orquestrar transação de persistência | UI, PROD, REPO, AUDIT, ALERT | HU02, HU03; RF04, RF05, RF06, RF07, RNF03, RNF08 |
| Repositório Persistente (REPO) | Persistência local embarcada; transações atômicas; indexação; recuperação pós-crash | AUTH, PROD, MOV, AUDIT, QUERY, EXPORT | RNF02, RNF03, RNF05, RNF08 |
| Registro de Auditoria (AUDIT) | Armazenar registros imutáveis de operação (data, hora, usuário, detalhe) | MOV, REPO | RNF08; HU02, HU03, HU07 |
| Gerenciador de Alertas (ALERT) | Detectar produtos abaixo do limite, manter flags de alerta, expor notificações UI | PROD, MOV, UI | RF08, RF09; HU04 |
| Serviço de Consulta / Relatórios (QUERY) | Executar consultas de saldo e histórico com filtros/ordenadores, otimizado para performance | REPO, UI | RF10, RF11; HU06, HU07, RNF05 |
| Serviço de Exportação CSV (EXPORT) | Gerar arquivos CSV com esquema completo; permitir seleção de diretório; reportar sucesso/falha | REPO, FS, UI | HU08; RNF07 |
| Subsistema de Arquivos (FS) | APIs de escrita/leitura de arquivos locais para exportação/backup | EXPORT | HU08; RNF07 |

---

## 5. Bloqueios e Pendências

1. Política de usuários e permissões
   - Pendência: requisitos não detalham gerenciamento de usuários (criação, papéis, recuperação de senha, política de força de senha).
   - Impacto: decisão de autenticação e interface administrativa necessária.
   - Recomendação: definir roles mínimas (Operador, Administrador), regras de senha e fluxos de recuperação.

2. Concurrency / Multi-instância
   - Pendência: não especificado se o sistema será usado por múltiplos operadores simultaneamente (em rede) ou apenas por single-user local.
   - Impacto: afeta estratégia de armazenamento (single-file local vs. sincronização), resolução de conflitos e locking.
   - Recomendação: confirmar modelo de instalação (single estação vs. multi-estação). Se multi, definir mecanismo de sincronização/replicação.

3. Volume esperado de dados e limites de performance
   - Pendência: "grande volume" não quantificado.
   - Impacto: dimensionamento de índices, estratégia de paginação e garantias de RNF05.
   - Recomendação: solicitar estimativas (registros/ano, número de SKUs).

4. Formato CSV e campos obrigatórios
   - Pendência: layout/encoding/colunas do CSV não definido (se incluir IDs, timestamps ISO, separador).
   - Impacto: interoperabilidade com ferramentas externas e requisitos de compatibilidade regional (encodings, separador decimal).
   - Recomendação: padronizar schema CSV (colunas e ordenação) e encoding (ex.: UTF-8) antes da implementação.

5. Políticas de backup/restore
   - Pendência: frequência e estratégia de backup não especificadas.
   - Impacto: risco de perda de dados; obriga documentar instruções manuais para o usuário.
   - Recomendação: definir procedimentos de exportação automática opcional e instruções de restauração.

6. Localização/idioma e formatos de data/número
   - Pendência: não especificado; importante para apresentação e CSV.
   - Recomendação: confirmar configuração regional padrão e permitir seleção local.

7. Tratamento de fuso horário/timestamps
   - Pendência: RNF08 exige data e hora, mas não define fuso horário.
   - Impacto: histórico e auditoria podem ficar inconsistentes se fuso não padronizado.
   - Recomendação: registrar timestamps com timezone local e incluir offset no CSV/auditoria.

---

## 6. Cobertura de Requisitos

Resumo de rastreabilidade (mapeamento requisito → componente / decisão principal):

Funcionais (RF):
- RF01 (cadastro produtos) → UI (formulário), PROD (validação unicidade, persistência)  
- RF02 (editar produto) → UI, PROD, REPO  
- RF03 (remover produto) → UI, PROD, REPO (verificar integridade histórica antes de remover)  
- RF04 (registrar entrada) → UI, MOV (entrada), PROD, REPO, AUDIT  
- RF05 (registrar saída) → UI, MOV (saída), PROD, REPO, AUDIT  
- RF06 (impedir saída > estoque) → MOV + PROD (validação pré e na transação)  
- RF07 (atualizar saldo automaticamente) → MOV + PROD + REPO (transação atômica)  
- RF08 (configurar limite mínimo) → UI, PROD, REPO  
- RF09 (emitir alerta visível) → ALERT + UI, acionado por MOV/PROD após atualização  
- RF10 (exibir saldo atual) → UI + QUERY + PROD + REPO  
- RF11 (consultar histórico por produto/periodo) → QUERY + REPO + UI  
- RF12 (pesquisar por nome) → UI + QUERY + REPO (índice/filtragem)

Não Funcionais (RNF):
- RNF01 (desktop Windows) → Implantação: build desktop; UI deve cumprir paradigmas desktop. (Decisão: monolítico modular desktop)  
- RNF02 (persistência local embarcada) → REPO conceitual (DB embarcado + WAL)  
- RNF03 (garantir não perda em fechamento inesperado) → REPO (transações atômicas + journaling), gravação síncrona/flush onde necessário  
- RNF04 (usabilidade: ≤3 interações) → UI design (scripts de fluxo, operações rápidas)  
- RNF05 (desempenho: carregar em ≤2s) → QUERY + REPO (índices, projeções, paginação)  
- RNF06 (autenticação) → AUTH + REPO (armazenamento seguro)  
- RNF07 (exportar CSV) → EXPORT + FS + UI  
- RNF08 (registro data/hora/usuário) → AUDIT + MOV + REPO

Observações adicionais:
- HU acceptance criteria são cobertos pelos componentes acima; pontos operacionais (ex.: campos obrigatórios, validações) implementados nas camadas UI e serviços (PROD/MOV).

---

## 7. Gap Analysis

1. Gestão de usuários e autorização
   - Lacuna: especificação não descreve criação/remoção de usuários, papéis, recuperação de senha, política de complexidade.
   - Impacto arquitetural: AUTH precisa de componente administrativo; sem isso, suporte e segurança ficam limitados.
   - Ação recomendada: definir requisitos de administração de usuários (mínimo: criar usuário administrador e operadores; política de senha; bloqueio por tentativas).

2. Concurrency e uso multi-estação
   - Lacuna: não está claro se múltiplas instâncias/estações acessarão o mesmo armazenamento.
   - Impacto: se houver multi-estações, REPO embarcado único não basta; será preciso sincronização/replicação ou arquitetura cliente/servidor.
   - Ação recomendada: confirmar modelo de implantação. Se multi, especificar mecanismo de sincronização, resolução de conflitos e locking.

3. Volume e SLAs de desempenho não quantificados
   - Lacuna: "grande volume" indefinido.
   - Impacto: dimensionamento de índices, escolha de estratégia de paginação e limites de memória.
   - Ação recomendada: obter estimativas (nº produtos, movimentações por dia/ano) para calibrar índices e necessidades de I/O.

4. Esquema/encoding e metadados do CSV
   - Lacuna: formato de CSV (colunas, separador, encoding) não definido.
   - Impacto: interoperabilidade para backup e análise externa.
   - Ação recomendada: especificar schema CSV (colunas obrigatórias, formato ISO8601 para timestamps, UTF-8, separador configurable).

5. Backup/restore e políticas operacionais
   - Lacuna: falta definição de mecanismos e frequência de backup, e procedimentos de restauração.
   - Impacto: risco operacional e suporte em caso de corrupção de dados.
   - Ação recomendada: definir rotina de exportação automática opcional, instruções de restauração e verificação de integridade.

6. Política de retenção e arquivamento de movimentações
   - Lacuna: retenção histórica indefinida (quanto manter no primário vs arquivar).
   - Impacto: crescimento de tamanho do banco e performance.
   - Ação recomendada: definir retenção e política de arquivamento (ex.: compactação/exportação por período).

7. Tratamento de horas/fuso horário e sincronização de relógio
   - Lacuna: especificação apenas pede data/hora; não define fuso/offset.
   - Impacto: registros de auditoria podem ficar ambíguos se estação tiver clock errado.
   - Ação recomendada: padronizar gravação em ISO8601 com offset local; log de alterações de relógio e instruções para sincronização NTP quando aplicável.

8. Regras de negócio ausentes para remoção de produto com histórico
   - Lacuna: RF03 permite remoção, mas não define comportamento quando existem movimentações históricas.
   - Impacto: perda de integridade referencial/auditoria se produto físico for apagado.
   - Ação recomendada: definir política: soft-delete (marcar inativo) e manter histórico imutável; permitir exclusão física apenas se sem histórico.

9. Mensagens de erro e internacionalização
   - Lacuna: detalhes de mensagens de erro, linguagem padrão e necessidades de tradução.
   - Impacto: usabilidade e suporte.
   - Ação recomendada: definir catálogo de mensagens, permitir configuração de idioma e padrões de texto de erro.

10. Testes de integridade e critérios de aceitação automatizados
    - Lacuna: critérios de aceitação funcionais existem, mas não há definição de testes automatizados e métricas de aceitação para RNFs.
    - Impacto: dificulta verificação automatizada de requisitos críticos (durability, performance).
    - Ação recomendada: definir suíte de testes (UI, integração, stress), cenários de crash/recovery e SLAs de performance para validação.

---

Resumo final
- A arquitetura proposta é um monólito modular desktop com componentes bem definidos para UI, autenticação, domínio (produto/movimentação), persistência local com journaling, alerta e exportação.  
- Os requisitos funcionais e não-funcionais descritos são mapeados para componentes e decisões claras.  
- Existem gaps operacionais e de políticas (usuários, multi-instância, CSV/schema, backup, retenção) que devem ser resolvidos antes da implementação detalhada para reduzir riscos arquiteturais.

Se desejar, posso:
- Gerar modelos de dados conceituais (DDL conceptual) sem vincular a tecnologia específica;  
- Produzir telas de fluxo (wireframes textuais) para garantir RNF04 (≤3 interações);  
- Fornecer checklist de testes de recuperação/crash para validar RNF03.