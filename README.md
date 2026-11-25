# Diário escolar

Aplicativo desktop em Python e Tkinter com banco de dados SQLite. O sistema foi modelado a partir da planilha “Planilha_de_Notas_Escola (1).xlsx”, que veio sem alunos cadastrados.

## Como executar

1. Extraia o ZIP para uma pasta em que você possa gravar arquivos.
2. Abra um terminal nessa pasta e execute:

   ```bash
   python escola.py
   ```

   Use `python3 escola.py` se esse for o comando disponível. É necessário ter Python 3.10 ou superior com Tkinter. Para conferir o Tkinter, execute `python -m tkinter`. No Ubuntu ou Debian, ele pode ser instalado com `sudo apt install python3-tk`.

## Como usar

1. Clique em **Novo** e informe escola, professor(a), disciplina e turma.
2. Selecione o diário e clique em **Cadastrar aluno**. Informe o número de chamada e o nome. O número deve ser único no diário.
3. Lance as notas nas abas dos três trimestres. Use **Editar aluno e notas** para consultar ou atualizar o cadastro e os lançamentos.
4. Use os botões **Editar** e **Excluir** para gerenciar o diário. A exclusão de um diário também apaga os alunos e notas vinculados a ele. A interface pede confirmação antes de excluir.

## Regras de notas

- **N1** soma a prova de até 6 pontos e o instrumento de até 4 pontos.
- **N2** soma dois instrumentos de até 5 pontos cada.
- **N3** corresponde à prova de até 10 pontos.
- A média trimestral considera os totais disponíveis de N1, N2 e N3. A média final considera as médias trimestrais disponíveis. Assim como na planilha, uma nota zero entra na média, um grupo totalmente vazio fica de fora e um grupo parcialmente preenchido já tem seu total calculado.
- Os cálculos usam os valores originais. A interface mostra duas casas decimais e aceita vírgula ou ponto na digitação.

O arquivo `escola.sqlite3` é criado ao lado de `escola.py` na primeira execução e guarda os dados entre sessões. Para fazer uma cópia de segurança, feche o aplicativo e copie esse arquivo.
