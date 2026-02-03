#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta** | Stitch (anteriormente Galileo AI)                                              |
| **Fabricante / Comunidade** | Google (Labs / Area 120)                                                       |
| **Site oficial / documentação** | https://stitch.withgoogle.com/                                                 |
| **Tipo de ferramenta** | Plataforma de prototipagem técnica (Design-to-Code) assistida por IA           |
| **Licença / acesso** | Experimental / Acesso via convite ou conta Google Workspace                    |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa** | LLM Multimodal (focado em UI, Interatividade e Código)       |
| **Nome do Modelo** | Família Gemini (integrado nativamente)                       |
| **Versão** | Gemini 1.5 Pro (base para geração de lógica e componentes)   |
| **Tamanho (nº de parâmetros)** | Não divulgado                                                |
| **Acesso** | Cloud (Interface Web "Canvas-first")                         |
| **Suporte a Fine-tuning** | Não                                                          |
| **Suporte a RAG** | Sim (analisa componentes e contexto do projeto atual)         |
| **Métodos de prompting suportados** | Linguagem natural, feedback visual e iteração via chat       |
| **Ferramentas adicionais** | Editor de código integrado, Preview real-time e Publicação   |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?** | Cloud (Navegador)                       |
| **Infraestrutura utilizada no teste** | Google Cloud Platform (GCP)             |
| **Custos (quando aplicável)** | Atualmente gratuito (estágio experimental) |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

Para cada item abaixo, descreva:

* **O que a ferramenta faz**: Reduz o gap entre design e front-end, gerando código funcional a partir de descrições ou prints.
* **Como faz**: Utiliza modelos Gemini para interpretar prompts e gerar simultaneamente a UI (visual) e a lógica (código React/Frameworks Web).
* **Exemplos / evidências**: Converter um print de uma interface de chat em um componente funcional com Tailwind CSS.
* **Limitações observadas**: Foco excessivo em interface; lógica de backend pesada e segurança de dados complexa ainda exigem intervenção manual.

---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações                                      |
| ----------------------- | --------------------- | ------------------------------------------------------------ |
| Elicitação              | Sim                   | Ajuda a dar forma aos requisitos através de protótipos rápidos |
| Análise                 | Sim                   | Permite validar a viabilidade de fluxos de usuário           |
| Priorização             | N/A                   | Não suportado explicitamente                                 |
| Modelagem               | Sim                   | Gera modelos de dados e arquitetura de componentes           |
| Validação / Verificação | Sim                   | Protótipos "vivos" para teste de uso imediato                |
| Documentação            | Parcial               | O código gerado é autoexplicativo e comentado                |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações                                      |
| -------------------------------- | --------------------- | ------------------------------------------------------------ |
| Geração de designs arquiteturais | Parcial               | Define a estrutura de navegação e hierarquia de componentes   |
| Decisões arquiteturais           | N/A                   | Fora do escopo (decisões de infraestrutura/servidor)          |
| Avaliação de trade-offs          | N/A                   | Não aplicável                                                |
| Uso de padrões arquiteturais     | Parcial               | Aplica padrões de UI/UX e organização de pastas front-end    |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações                                      |
| ---------------------------------- | --------------------- | ------------------------------------------------------------ |
| Sugestão/uso de padrões de projeto | Parcial               | Criação de componentes reutilizáveis e sistemas de design      |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações                                      |
| ----------------- | --------------------- | ------------------------------------------------------------ |
| Geração de código | Sim                   | Geração de código limpo e moderno (React/JS/Tailwind)        |
| Refatoração       | Sim                   | Capacidade de pedir à IA para otimizar o código via chat     |
| Detecção de bugs  | Sim                   | Identificação automática de erros de sintaxe no editor       |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | N/A                   | Não suportado            |
| Execução de testes automatizados                 | N/A                   | Não suportado            |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações        |
| --------------------------------- | --------------------- | ------------------------------- |
| CI/CD                             | N/A                   | Fora do escopo                  |
| Automação                         | Parcial               | Automação de processos de design |
| Monitoramento                     | N/A                   | Não aplicável                   |
| Documentação técnica automatizada | Parcial               | Especificações visuais automáticas |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações           |
| ----------------------- | --------------------- | ---------------------------------- |
| Correções automatizadas | Parcial               | Ajustes automáticos de UI/Layout   |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações        |
| ----------------------------------- | --------------------- | ------------------------------- |
| Planejamento                        | Parcial               | Quadros e definição de fluxos   |
| Execução                            | Parcial               | Colaboração em tempo real       |
| Controle                            | Parcial               | Histórico de versões do projeto |
| Encerramento                        | N/A                   | Não suportado                   |
| Gestão de riscos                    | N/A                   | Não aplicável                   |
| Estimativas (tempo, custo, esforço) | N/A                   | Não aplicável                   |
| Medição                             | N/A                   | Não aplicável                   |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações                                      |
| ----------------------------------- | ---------------- | ------------------------------------------------ |
| Precisão                            | ⭐⭐⭐⭐⭐            | Alta fidelidade entre o prompt e o resultado     |
| Profundidade técnica                | ⭐⭐⭐⭐             | Gera lógica funcional, não apenas visual         |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            | Entende o estado global da aplicação             |
| Clareza                             | ⭐⭐⭐⭐⭐            | Interface extremamente intuitiva                 |
| Aderência às melhores práticas      | ⭐⭐⭐⭐             | Segue padrões modernos de desenvolvimento web    |
| Ocorrência de alucinações           | Baixa            | IA é bem guiada pelos componentes existentes     |

---
#  **6. Experimentos Realizados**

### ● Geração automática de telas de interface a partir de prompts em linguagem natural.

### ● Criação de protótipo de alta fidelidade para um sistema web fictício.

### ● Ajustes automáticos de layout e tipografia sugeridos pela IA.

### ● Uso do Dev Mode para inspeção de estilos e exportação de trechos de código CSS.


## Resultados quantitativos
### Usando IA
* Tempo: 30 minutos.
* Número de erros: 2.
* Qualidade do código: Alta.
* Cobertura de testes: Alta. 
* Documentação: Completa.

### Sem uso de IA
* Tempo: 5 horas.
* Número de erros: Inúmeros.
* Qualidade do código: Variável.
* Cobertura de testes: Baixa. 
* Documentação: Totalmente ignorada no rascunho.

### ● Exemplos (copie trechos de código, respostas etc.)
### Usando IA
Trecho do Código: 
<!-- Bottom Navigation Bar -->
<div class="fixed bottom-0 left-0 right-0 h-20 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-lg border-t border-gray-200 dark:border-gray-700">
<div class="flex h-full items-center justify-around">
<button class="flex flex-col items-center gap-1 text-primary">
<span class="material-symbols-outlined !font-bold" style="font-variation-settings: 'FILL' 1, 'wght' 700;">home</span>
<span class="text-xs font-bold">Início</span>
</button>
<button class="flex flex-col items-center gap-1 text-gray-500 dark:text-gray-400">
<span class="material-symbols-outlined">category</span>
<span class="text-xs">Categorias</span>
</button>
<button class="flex flex-col items-center gap-1 text-gray-500 dark:text-gray-400">
<span class="material-symbols-outlined">favorite</span>
<span class="text-xs">Favoritos</span>
</button>
<button class="flex flex-col items-center gap-1 text-gray-500 dark:text-gray-400">
<span class="material-symbols-outlined">person</span>
<span class="text-xs">Perfil</span>
</button>
</div>
</div>
</div>
</body></html>

### Sem usar IA
Trecho de Código CSS:

body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
}

header {
    background-color: #ffb6c1;
    text-align: center;
    padding: 20px;
}

nav {
    background-color: #333;
    text-align: center;
    padding: 10px;
}

nav a {
    color: white;
    margin: 0 15px;
    text-decoration: none;
}

---

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**
* **Abordagem Canvas**: Visualização em tempo real da construção da aplicação.
* **Hibridismo**: Liberdade total para alternar entre prompts de IA e edição manual de código.
* **Velocidade de MVP**: Redução drástica do tempo entre conceito e produto funcional.

### **Limitações**
* **Ecossistema Fechado**: Otimizada para o stack técnico suportado pelo Google.
* **Maturidade Beta**: Funcionalidades podem sofrer alterações bruscas e instabilidades.

---

#  **8. Riscos, Custos e Considerações de Uso**

* **Dependência de vendor**: O Stitch é intrinsecamente ligado à infraestrutura do Google e aos modelos Gemini; não há portabilidade direta da inteligência para outros provedores.
* **Limitações em privacidade ou compliance**: Execução cloud-first; os prompts e o código são processados externamente, exigindo avaliação de políticas de confidencialidade.
* **Barreiras técnicas de adoção**: Requer adaptação dos desenvolvedores para um fluxo de trabalho baseado em prompts e edição assistida.
* **Dificuldades de execução local**: Ferramenta exclusivamente online; impossibilidade de uso offline.
* **Restrições para fine-tuning ou RAG**: Não há suporte formal para o usuário treinar o modelo com bases de código privadas proprietárias.

---

#  **9. Conclusão Geral da Análise**

* A ferramenta é adequada para as atividades de prototipagem técnica, construção de front-end, validação de UX e criação de MVPs funcionais.
* **Os casos deve ser evitada: Sistemas puramente backend, lógica de negócio crítica off-cloud ou sistemas de baixa latência/nível.
* A maturidade técnica que se encontra é na fase Experimental (Labs), mas com alta funcionalidade prática.
* Vale a pena para a organização, especialmente para acelerar ciclos de inovação e reduzir o gap entre design e engenharia.

---

#  **10. Referências e Links Consultados**

* Site Oficial Stitch: https://stitch.withgoogle.com/

---

#  **Nota de Histórico**
> **Observação:** Esta ferramenta, agora denominada **Stitch**, era anteriormente conhecida como **Galileo AI**. A tecnologia foi integrada e evoluída dentro do ecossistema do Google para focar na criação de aplicações completas através de uma interface de tela (canvas).