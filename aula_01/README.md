# Laboratório Prático: Modelagem Informacional - Aula 01 (FUCAPE)

Bem-vindo ao repositório do laboratório prático da **Aula 01 de Modelagem Informacional**. Neste laboratório, simulamos os dados de uma empresa fictícia, a "Varejista Multicanal", que possui dados armazenados em diferentes formatos (estruturados, semi-estruturados e não estruturados).

## Objetivo do Laboratório

Explorar e compreender as características, vantagens e desafios da extração e manipulação de diferentes modelos de dados usando Python e Pandas.

## Artefatos do Repositório

*   **`varejo_erp.db`**: Banco de dados SQLite contendo dados transacionais estruturados e fortemente tipados (relacional).
*   **`logs_app.json`**: Arquivo JSON contendo eventos de navegação de um app móvel, com esquema flexível e aninhado (semi-estruturado).
*   **`sac_texto_livre.csv`**: Arquivo CSV com feedbacks e reclamações do SAC, em linguagem natural, contendo gírias e ambiguidades (não estruturado).

---

## Como Executar no Google Colab (Recomendado)

O Google Colab é a ferramenta recomendada para este laboratório, pois não requer instalação no seu computador.

### Passo a Passo:

1. Faça o download deste repositório ou dos seguintes arquivos para o seu computador:
   *   `varejo_erp.db`
   *   `logs_app.json`
   *   `sac_texto_livre.csv`

2. Acesse o [Google Colab](https://colab.research.google.com/).
3. Quando o notebook abrir, localize o painel lateral esquerdo e clique no ícone de **"Arquivos"** (uma pastinha).
4. Clique no ícone de upload (uma folha com uma seta para cima) ou simplesmente arraste e solte os 3 arquivos de dados (`varejo_erp.db`, `logs_app.json`, `sac_texto_livre.csv`) para dentro dessa aba de arquivos.
   > **Atenção:** Os arquivos enviados dessa forma são temporários. Se a sessão do Colab desconectar, você precisará fazer o upload deles novamente.
5. Pronto! Agora você pode rodar as células do notebook sequencialmente clicando no botão "Play" ao lado de cada uma (ou usando o atalho `Shift + Enter`).

---

## Como Executar Localmente (VS Code / Jupyter Lab)

Se preferir rodar localmente no seu ambiente:

1. Clone ou baixe este repositório para uma pasta local.
2. Certifique-se de ter o Python instalado, além das bibliotecas necessárias (Pandas). Instale executando no terminal:
   ```bash
   pip install pandas
   ```
   *(As bibliotecas sqlite3 e json já são nativas do Python)*.
3. Abra a pasta no seu editor favorito (como VS Code ou inicie o Jupyter Lab).
4. Como os arquivos de dados estão na mesma pasta do notebook, basta executar as células normalmente.

Boa prática!
