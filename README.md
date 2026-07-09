# APP Fichas Tecnicas

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## IDEALIZACAO DO PROJETO

Este app foi desenvolvido porque diversos clientes apresentavam dificuldade para parametrizar seus produtos e precifica-los de forma eficiente de acordo com seus gastos reais.

Muitos pequenos empresarios conhecem bem a producao, mas nem sempre possuem uma ferramenta simples para transformar receitas, insumos, rendimento, perdas e custos em uma ficha tecnica clara. O objetivo deste projeto e automatizar varias dessas etapas e, principalmente, ajudar o empresario a compreender como calcular os custos de um produto, como definir precos de venda e como padronizar os processos de fabricacao.

> **Versao demo:** a versao exposta neste GitHub e uma demonstracao publica do projeto. A versao final e privada, possui recursos comerciais e ajustes especificos de clientes, e nao pode ser exibida de forma completa na rede.

## SOBRE O APP

O App de Fichas Tecnicas e uma aplicacao desktop/local criada em Python. Ele permite cadastrar ingredientes, montar fichas tecnicas, calcular custos, apoiar a precificacao e gerar PDFs para consulta ou impressao.

O app foi pensado para pequenos negocios, como:

- padarias;
- confeitarias;
- cozinhas;
- lanchonetes;
- restaurantes;
- pequenas fabricas de alimentos;
- produtores artesanais.

## FUNCIONALIDADES

- Cadastro de ingredientes.
- Cadastro de produtos.
- Cadastro de fichas tecnicas.
- Cadastro de etapas de preparo.
- Produtos compostos, permitindo usar uma ficha como insumo de outra.
- Calculo de custo total da receita.
- Calculo de custo por unidade.
- Calculo de custo por porcao.
- Calculo de custo por kg, quando aplicavel.
- Apoio a precificacao.
- Deteccao de ciclos em produtos compostos.
- Geracao de PDF da ficha tecnica.
- Geracao de etiquetas em PDF.
- Banco de dados local em Excel.
- Backups locais automaticos.
- Estrutura preparada para gerar executavel Windows com PyInstaller.

## LAYOUT E MODO DE USAR

Ao abrir o aplicativo, o usuario tem acesso as principais areas de cadastro, calculo e emissao de documentos da ficha tecnica.

![imageFichas1](https://github.com/user-attachments/assets/103c7a22-abe6-4d10-a2c2-5ab93bb15024)

### 1. Cadastre os ingredientes

O primeiro passo e cadastrar os ingredientes usados na producao.

Exemplos:

- farinha de trigo;
- ovos;
- leite;
- fermento;
- acucar;
- recheios;
- embalagens;
- coberturas.

Esses ingredientes serao usados posteriormente nas fichas tecnicas.

![imageFichas2](https://github.com/user-attachments/assets/ba142998-aec0-4877-8807-571f110b6572)

### 2. Cadastre o produto

Depois de cadastrar os ingredientes, crie um produto e informe os dados principais, como nome, rendimento, tipo da ficha e informacoes complementares.

### 3. Monte a ficha tecnica

Na ficha tecnica, informe quais ingredientes fazem parte do produto e suas respectivas quantidades.

O sistema usa essas informacoes para calcular o custo da receita.

![imageFichas3](https://github.com/user-attachments/assets/6cda6e57-87e9-4d21-8a7f-7d5898413abe)

### 4. Use produtos compostos quando necessario

Caso uma preparacao seja usada dentro de outra receita, ela pode ser cadastrada como produto composto.

Exemplo:

- massa base;
- recheio;
- cobertura;
- calda;
- produto final.

Isso ajuda a organizar receitas mais complexas sem perder o controle dos custos.

### 5. Analise custos e precificacao

Com a ficha preenchida, o app calcula custos e ajuda o usuario a entender melhor a formacao de preco.

Essas informacoes apoiam decisoes sobre:

- preco de venda;
- margem;
- rendimento;
- perdas;
- padronizacao;
- viabilidade do produto.

![imageFichas4](https://github.com/user-attachments/assets/8ac141f1-0583-467f-9a3d-de406d8d7ba6)

### 6. Gere PDFs

O app permite gerar PDFs das fichas tecnicas.

Os arquivos sao salvos em:

```text
pdfs/
```

![imageFichas5](https://github.com/user-attachments/assets/6205666f-8b1d-4605-ad1f-dd1e4bec1547)

### 7. Gere etiquetas

Tambem e possivel gerar etiquetas em PDF para ingredientes.

Os arquivos sao salvos em:

```text
pdfs/etiquetas/
```

## TECNOLOGIAS UTILIZADAS

## Back end

- Python
- openpyxl
- ReportLab

## Front end

- Tkinter
- ttkbootstrap

## Testes e empacotamento

- pytest
- PyInstaller

## COMO EXECUTAR O PROJETO

Pre-requisitos:

- Python 3.10 ou superior.

```bash
# clonar repositorio
git clone https://github.com/Miguel-Olimpio/APP-FichasTecnicas.git

# entrar na pasta do projeto
cd APP-FichasTecnicas

# criar ambiente virtual opcional
python -m venv .venv

# ativar ambiente virtual no Windows
.venv\Scripts\activate

# instalar dependencias
pip install -r requirements.txt

# executar o projeto
python main.py
```

Tambem e possivel executar:

```bash
python -m app.main
```

## BANCO DE DADOS LOCAL

O app utiliza planilhas Excel como banco de dados local.

Na primeira execucao, o sistema cria automaticamente as pastas necessarias:

```text
data/
pdfs/
backups/
```

Arquivos principais:

```text
data/banco_fichas.xlsx
data/banco_ingredientes.xlsx
```

Esses arquivos nao sao versionados no GitHub, pois podem conter dados reais de clientes.

## TESTES

Para rodar os testes:

```bash
python -m pytest tests -q
```

## GERAR EXECUTAVEL

Para gerar o executavel Windows:

```bash
pyinstaller --clean --noconfirm FichasTecnicas.spec
```

O executavel sera criado em:

```text
dist/FichasTecnicas/FichasTecnicas.exe
```

Estrutura esperada para distribuicao:

```text
FichasTecnicas/
  FichasTecnicas.exe
  data/
  pdfs/
  backups/
  icon/
```

## ESTRUTURA DO PROJETO

```text
app/
  config/
  models/
  repositories/
  services/
  ui/
  utils/
  pdf/
tests/
icon/
pyinstaller_hooks/
main.py
requirements.txt
FichasTecnicas.spec
```

## OBSERVACOES

- Esta e uma versao demo.
- A versao comercial completa e privada.
- Arquivos de dados, PDFs, backups e builds nao sao enviados ao GitHub.
- O app foi desenvolvido para uso desktop/local.
- A persistencia demonstrativa utiliza Excel local.

## AUTOR

Miguel Olimpio de Paula Netto

## LICENCA

Este projeto esta sob licenca MIT. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
