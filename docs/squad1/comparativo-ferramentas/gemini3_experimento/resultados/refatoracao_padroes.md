# Refatoração e Design Patterns: Notification Module

Este documento apresenta a refatoração do módulo de notificações do `AlertService`, substituindo a lógica condicional complexa pelo padrão de projeto **Strategy**, visando extensibilidade e testabilidade.

## 1. Refatoração Proposta: Strategy Pattern

O problema identificado é o uso excessivo de `if/else` ou `switch/case` para determinar qual canal de notificação utilizar (Slack, Email, PagerDuty). Isso viola o **Open/Closed Principle (OCP)** do SOLID, pois a classe principal precisa ser modificada toda vez que um novo canal é adicionado.

A solução é aplicar o **Strategy Pattern**.
*   **Conceito:** Definir uma família de algoritmos (estratégias de notificação), encapsular cada um deles em uma classe separada e torná-los intercambiáveis.
*   **Aplicação:** Criaremos uma interface comum `NotificationStrategy`. Cada canal (Slack, Email, etc.) será uma implementação concreta dessa interface. O serviço principal (`NotificationService`) apenas delegará a execução para a estratégia correta, sem conhecer os detalhes de implementação de cada canal.

## 2. Implementação (Java + Spring Boot)

Abaixo, a implementação utilizando recursos do Spring Boot para injeção de dependência dinâmica das estratégias.

### 2.1. Enum para Tipos de Notificação

```java
package com.criticalevent.alertservice.domain;

public enum NotificationType {
    SLACK,
    EMAIL,
    PAGER_DUTY;
}
```

### 2.2. Interface da Estratégia (Strategy Interface)

```java
package com.criticalevent.alertservice.strategy;

import com.criticalevent.alertservice.domain.NotificationType;
import com.criticalevent.alertservice.dto.AlertDTO;

public interface NotificationStrategy {
    
    /**
     * Envia a notificação para o canal específico.
     */
    void send(AlertDTO alert);

    /**
     * Identifica qual tipo de notificação esta estratégia suporta.
     */
    NotificationType supports();
}
```

### 2.3. Implementações Concretas (Concrete Strategies)

**Slack Strategy:**

```java
package com.criticalevent.alertservice.strategy.impl;

import com.criticalevent.alertservice.domain.NotificationType;
import com.criticalevent.alertservice.dto.AlertDTO;
import com.criticalevent.alertservice.strategy.NotificationStrategy;
import org.springframework.stereotype.Component;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Component
public class SlackNotificationStrategy implements NotificationStrategy {

    @Override
    public void send(AlertDTO alert) {
        log.info("Enviando notificação para o Slack: {}", alert.getMessage());
        // Lógica específica do Slack (WebClient, Payload format, etc.)
    }

    @Override
    public NotificationType supports() {
        return NotificationType.SLACK;
    }
}
```

**Email Strategy:**

```java
package com.criticalevent.alertservice.strategy.impl;

import com.criticalevent.alertservice.domain.NotificationType;
import com.criticalevent.alertservice.dto.AlertDTO;
import com.criticalevent.alertservice.strategy.NotificationStrategy;
import org.springframework.stereotype.Component;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Component
public class EmailNotificationStrategy implements NotificationStrategy {

    @Override
    public void send(AlertDTO alert) {
        log.info("Enviando email para destinatários configurados: {}", alert.getMessage());
        // Lógica específica de envio de Email (JavaMailSender, etc.)
    }

    @Override
    public NotificationType supports() {
        return NotificationType.EMAIL;
    }
}
```

### 2.4. Contexto / Serviço (Context)

Aqui utilizamos o poder do Spring. Ao injetar uma lista de `NotificationStrategy`, o Spring automaticamente encontra todos os beans que implementam essa interface. Criamos um mapa para acesso rápido (O(1)).

```java
package com.criticalevent.alertservice.service;

import com.criticalevent.alertservice.domain.NotificationType;
import com.criticalevent.alertservice.dto.AlertDTO;
import com.criticalevent.alertservice.strategy.NotificationStrategy;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class NotificationService {

    private final Map<NotificationType, NotificationStrategy> strategies;

    // O Spring injeta todas as implementações de NotificationStrategy encontradas no contexto
    public NotificationService(List<NotificationStrategy> strategyList) {
        this.strategies = strategyList.stream()
                .collect(Collectors.toMap(NotificationStrategy::supports, Function.identity()));
    }

    public void notify(AlertDTO alert, NotificationType type) {
        NotificationStrategy strategy = Optional.ofNullable(strategies.get(type))
                .orElseThrow(() -> new IllegalArgumentException("Canal de notificação não suportado: " + type));

        strategy.send(alert);
    }
}
```

## 3. Justificativa

A escolha do **Strategy Pattern** resolve os problemas de acoplamento e manutenção das seguintes formas:

1.  **Adesão ao Open/Closed Principle (OCP):**
    *   O código está **aberto para extensão**: Para adicionar um novo canal (ex: SMS ou Microsoft Teams), basta criar uma nova classe que implemente `NotificationStrategy` e anotá-la com `@Component`.
    *   O código está **fechado para modificação**: A classe `NotificationService` não precisa ser alterada. O Spring injetará a nova estratégia automaticamente na lista, e o mapa será atualizado na inicialização. Não há mais `if/else` para tocar.

2.  **Facilidade de Testes Unitários (Testability):**
    *   Como as lógicas de envio estão isoladas em classes separadas (`SlackNotificationStrategy`, `EmailNotificationStrategy`), podemos testar cada uma individualmente sem se preocupar com as outras.
    *   Para testar o `NotificationService`, podemos facilmente "mockar" as estratégias. Não precisamos configurar um servidor de email ou slack real; basta injetar um mock de `NotificationStrategy` que verifica se o método `send` foi chamado corretamente.

3.  **Redução da Complexidade Ciclomática:**
    *   Removemos estruturas condicionais aninhadas da classe de serviço, tornando o código mais legível e menos propenso a erros (bugs) ao alterar a lógica de um canal específico.
