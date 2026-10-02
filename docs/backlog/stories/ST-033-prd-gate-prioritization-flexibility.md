# STORY ST-033: Flexibilização de Priorização no PRDQualityGate

> **Épico:** EP-007  
> **Status:** IN_PROGRESS  
> **Responsáveis:** @turing, @grace  
> **Prioridade:** MÉDIA  

---

## 1. Descrição & Valor
Como Product Manager,  
Quero que o `PRDQualityGate` valide a presença de uma metodologia formal de priorização (RICE, WSJF, MoSCoW, ICE),  
Para que projetos possam adotar o critério de priorização mais adequado sem amarrações rígidas a uma única sigla.

---

## 2. Critérios de Aceite (BDD)

### Cenário 1: PRD com MoSCoW ou WSJF é aprovado
* **Dado** um PRD contendo a seção "Critérios MoSCoW" ou "Priorização WSJF"
* **Quando** o `PRDQualityGate.evaluate` for executado
* **Então** o gate deve considerar o critério formal de priorização atendido.
