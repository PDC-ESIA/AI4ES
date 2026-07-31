# Relatório — Duas PoCs sobre Segurança e Confiabilidade do Sistema

## PoC 1: Sandbox em Nuvem (Daytona)

### Objetivo da PoC

Avaliar o uso de um ambiente isolado e remoto (sandbox), hospedado na nuvem, para que os agentes do sistema pudessem criar, executar e gerenciar código de forma segura e separada do restante da infraestrutura do projeto.

### Motivo da Inviabilidade

A solução testada dependia integralmente de um serviço de nuvem de terceiros para toda a execução dos agentes. Isso expõe o sistema a riscos considerados inaceitáveis para uma capacidade crítica do projeto:

- **Latência**: cada ação dos agentes passaria por uma chamada de rede externa, tornando o sistema mais lento e menos previsível.
- **Dependência de internet**: qualquer instabilidade ou queda de conexão interromperia a execução dos agentes por completo.
- **Dependência de terceiros**: o funcionamento do sistema ficaria condicionado à disponibilidade e ao desempenho de um provedor externo, fora do controle da equipe.

### Conclusão

A parte técnica da solução funcionou como esperado durante os testes. A inviabilidade não está na tecnologia em si, mas na decisão estratégica de não tornar uma capacidade essencial do sistema dependente de um serviço em nuvem externo.

### Encaminhamento

Foi decidido não avançar com esta PoC no formato proposto

---

## PoC 2: Confirmação Humana no Fluxo Automático (Orchestrator)

### Objetivo da PoC

Estender a trava de segurança já existente — que pausa a execução e pede aprovação humana antes de criar um arquivo — para dentro do fluxo automático completo do sistema (Orchestrator), que hoje roda sozinho do início ao fim sem intervenção manual no meio do caminho.

### Motivo da Inviabilidade

Para a trava de segurança funcionar dentro do fluxo automático, seria necessário fazer várias alterações no próprio Orchestrator, entre elas:

- Ensiná-lo a enxergar e lidar com partes internas de uma etapa, não só a etapa como um todo.
- Redesenhar como ele retoma o controle depois que uma aprovação humana acontece no meio de uma etapa — hoje, ao tentar corrigir isso, o sistema passou a "pular" o Orchestrator e falar direto com a parte interna que pausou, tirando dele justamente a função de decidir o que acontece a seguir.
- Verificar e garantir que essas mudanças não afetem a etapa de testes, que já tem hoje um mecanismo parecido de pausa/aprovação funcionando corretamente.

Como o Orchestrator é usado por **todo** o fluxo automático, não só pela etapa de código, qualquer alteração nele tem potencial de afetar partes do sistema que já funcionam corretamente hoje. Ou seja: o que começou como um ajuste pontual se tornaria uma mudança estrutural em um componente central e sensível do sistema. Além do fato, de isso adicionaria mais dependêcia ao Orchestrator.

### Conclusão

A dificuldade não está na trava de segurança em si, que continua funcionando normalmente quando usada de forma isolada. A inviabilidade está no volume e na profundidade das mudanças que seriam necessárias no Orchestrator para sustentar essa proteção dentro do fluxo automático completo — um risco desproporcional ao benefício buscado nesta PoC.

### Encaminhamento

Foi decidido não avançar com esta PoC no formato proposto

---

## Aprendizados Gerais das Duas PoCs

### Sandbox em Nuvem (Daytona)

- **Compreensão de isolamento** Ao longo da investigação, foi aprendido sobre ideias isolamento em ambientes sandbox e sobre o poder de construção com o Daytona.

### Trava de Segurança (Confirmação Humana)

- **Compreensão do Orchestrator.** Compreensão sobre a capacidade de uso do Orchestrator para interromper o fluxo.