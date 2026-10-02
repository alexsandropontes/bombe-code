# STORY ST-032: Hardening do TuringReviewGate com Scanner Anti-Fraude

> **Épico:** EP-007  
> **Status:** IN_PROGRESS  
> **Responsáveis:** @turing, @aniche, @unclebob  
> **Prioridade:** ALTA  

---

## 1. Descrição & Valor
Como Tech Lead e QA Master,  
Quero que o `TuringReviewGate` impeça a aprovação de código fraudulento,  
Para que funções vazias com `NotImplementedError`, stubs vazios ou mocks enganosos em integração sejam vetados deterministicamente.

---

## 2. Critérios de Aceite (BDD)

### Cenário 1: Código com NotImplementedError é vetado
* **Dado** um código gerado que contém `raise NotImplementedError` ou `TODO` sem implementação
* **Quando** o `TuringReviewGate.evaluate` for executado com verificação de integridade
* **Então** o gate deve reprovar a entrega indicando a presença de código não implementado.

### Cenário 2: Código limpo e íntegro é aprovado
* **Dado** um código com testes automatizados passando e sem fraudes
* **Quando** o `TuringReviewGate.evaluate` for executado
* **Então** o gate deve aprovar a entrega.
