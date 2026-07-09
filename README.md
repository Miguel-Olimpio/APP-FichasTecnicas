# App de Fichas Tecnicas

Aplicativo desktop em Python para criacao, organizacao, calculo de custos, precificacao e geracao de fichas tecnicas de produtos alimenticios.

> **Versao demo:** esta versao publicada no GitHub e uma demonstracao do projeto. A versao final, utilizada em ambiente comercial, e privada e possui recursos, regras e ajustes especificos que nao podem ser exibidos integralmente em rede publica.

## Historia do desenvolvimento

Este app foi desenvolvido a partir de uma dificuldade recorrente observada em diversos clientes: muitos empresarios tinham problemas para parametrizar seus produtos, entender os custos reais de producao e definir precos de venda de forma eficiente.

A proposta do aplicativo e automatizar etapas importantes desse processo, mas principalmente ajudar o empresario a compreender como calcular o custo de um produto, como formar o preco de venda e como organizar os processos de fabricacao por meio de fichas tecnicas.

## Para que o app serve

O App de Fichas Tecnicas foi pensado para pequenos negocios, padarias, confeitarias, cozinhas, lanchonetes, restaurantes e produtores que precisam transformar receitas e processos em informacoes claras para gestao.

Com ele, e possivel:

- cadastrar ingredientes e seus custos;
- criar produtos e fichas tecnicas;
- montar receitas com ingredientes simples e produtos compostos;
- calcular custo total da receita;
- calcular custo por unidade, por porcao ou por kg;
- apoiar a precificacao de produtos;
- registrar etapas de preparo;
- gerar PDF da ficha tecnica;
- gerar etiquetas em PDF;
- manter os dados em planilhas Excel locais;
- gerar backups automaticos dos bancos de dados.

## Principais funcionalidades

- Cadastro de ingredientes.
- Cadastro de produtos.
- Cadastro de fichas tecnicas.
- Produtos compostos, permitindo que uma ficha use outro produto como insumo.
- Validacao para evitar ciclos entre produtos compostos.
- Calculo de custos com base nas quantidades e unidades informadas.
- Tela de precificacao.
- Geracao de PDF da ficha tecnica.
- Geracao de etiquetas de ingredientes.
- Persistencia local em Excel.
- Backups locais.
- Estrutura preparada para empacotamento com PyInstaller.

## Tecnologias utilizadas

- Python
- Tkinter
- ttkbootstrap
- openpyxl
- ReportLab
- PyInstaller
- pytest

## Como executar em ambiente de desenvolvimento

1. Clone o repositorio:

```bash
git clone https://github.com/Miguel-Olimpio/APP-FichasTecnicas.git
cd APP-FichasTecnicas
```

2. Crie e ative um ambiente virtual, se desejar:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Instale as dependencias:

```bash
pip install -r requirements.txt
```

4. Execute o app:

```bash
python main.py
```

Tambem e possivel executar:

```bash
python -m app.main
```

## Como usar o app

### 1. Cadastre ingredientes

Comece cadastrando os ingredientes usados nos seus produtos. Informe nome, unidade, custo e demais informacoes solicitadas pela tela.

Exemplos:

- farinha de trigo;
- leite;
- ovos;
- fermento;
- acucar;
- embalagens;
- recheios;
- coberturas.

Esses ingredientes servem de base para o calculo das fichas tecnicas.

### 2. Cadastre produtos e fichas tecnicas

Depois de cadastrar os ingredientes, crie os produtos. Em cada produto, informe os insumos utilizados e suas quantidades.

O app calcula automaticamente os custos de acordo com os dados cadastrados.

### 3. Use produtos compostos quando necessario

Se uma receita usa outra preparacao como parte do processo, ela pode ser tratada como produto composto.

Exemplo:

- massa base;
- recheio;
- cobertura;
- calda;
- produto final.

Isso ajuda a organizar producoes mais complexas sem perder o controle dos custos.

### 4. Analise custos e precificacao

Com a ficha tecnica preenchida, o app auxilia na leitura do custo total, custo por unidade, custo por porcao ou custo por kg.

Essas informacoes ajudam o empresario a tomar decisoes melhores sobre preco de venda, margem e padronizacao da producao.

### 5. Gere PDFs

O app permite gerar PDFs de fichas tecnicas para consulta, impressao ou compartilhamento interno.

Os arquivos sao salvos na pasta:

```text
pdfs/
```

### 6. Gere etiquetas

Tambem e possivel gerar etiquetas em PDF, salvas em:

```text
pdfs/etiquetas/
```

## Dados locais

O app usa planilhas Excel como banco de dados local.

Na primeira execucao, as pastas e arquivos necessarios sao criados automaticamente:

```text
data/
pdfs/
backups/
```

Principais arquivos locais:

```text
data/banco_fichas.xlsx
data/banco_ingredientes.xlsx
```

Esses arquivos nao sao versionados no GitHub, pois podem conter dados reais de clientes ou dados privados de operacao.

## Imagens da interface

As imagens demonstrativas podem ser adicionadas futuramente na pasta:

```text
docs/images/
```

Sugestao de organizacao:

```text
docs/images/dashboard.png
docs/images/ingredientes.png
docs/images/ficha-tecnica.png
docs/images/pdf.png
```

Depois de adicionar as imagens, elas podem ser referenciadas no README com Markdown:

```md
![Tela inicial](docs/images/dashboard.png)
```

## Testes

Para executar os testes:

```bash
python -m pytest tests -q
```

## Gerar executavel Windows

O projeto possui arquivo `.spec` para empacotamento com PyInstaller.

Para gerar o executavel:

```bash
pyinstaller --clean --noconfirm FichasTecnicas.spec
```

O executavel sera criado em:

```text
dist/FichasTecnicas/FichasTecnicas.exe
```

Ao distribuir a aplicacao, use a pasta gerada pelo PyInstaller e mantenha as pastas externas de dados ao lado do executavel:

```text
FichasTecnicas/
  FichasTecnicas.exe
  data/
  pdfs/
  backups/
  icon/
```

## Estrutura do projeto

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

## Observacoes importantes

- O projeto publicado e uma versao demo.
- A versao final/comercial e privada.
- Os arquivos em `data/`, `pdfs/`, `backups/`, `build/` e `dist/` nao devem ser enviados ao GitHub.
- O app foi desenvolvido para uso local/desktop.
- O armazenamento demonstrativo usa Excel local.

## Licenca

Este repositorio e disponibilizado publicamente apenas para demonstracao tecnica e apresentacao do projeto. A ausencia de uma licenca aberta significa que o uso, copia, distribuicao ou exploracao comercial do codigo depende de autorizacao do autor.
