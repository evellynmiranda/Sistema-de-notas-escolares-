"""Diário escolar trimestral com armazenamento em SQLite."""

import math
import sqlite3
import tkinter as tk
from contextlib import closing
from pathlib import Path
from tkinter import messagebox, ttk

IDENTIFICACAO = ("Escola", "Professor(a)", "Disciplina", "Turma")
AVALIACOES = (
    ("N1 · Prova", 6),
    ("N1 · Instrumento", 4),
    ("N2 · Instrumento 1", 5),
    ("N2 · Instrumento 2", 5),
    ("N3 · Prova", 10),
)
COLUNAS = tuple(f"t{tri}_a{nota}" for tri in range(1, 4) for nota in range(1, 6))


def media(valores):
    presentes = [valor for valor in valores if valor is not None]
    return sum(presentes) / len(presentes) if presentes else None


def calcular(notas):
    resultados = []
    for inicio in range(0, 15, 5):
        prova, instrumento, primeiro, segundo, n3 = notas[inicio:inicio + 5]
        n1 = None if prova is None and instrumento is None else (prova or 0) + (instrumento or 0)
        n2 = None if primeiro is None and segundo is None else (primeiro or 0) + (segundo or 0)
        resultados.append((n1, n2, n3, media((n1, n2, n3))))
    return resultados, media(trimestre[3] for trimestre in resultados)


def formatar(valor):
    return "—" if valor is None else f"{valor:.2f}".replace(".", ",")


def ler_nota(texto, limite):
    if not texto.strip():
        return None
    try:
        valor = float(texto.strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"Informe uma nota numérica de 0 a {limite}.") from None
    if not math.isfinite(valor) or not 0 <= valor <= limite:
        raise ValueError(f"A nota precisa estar entre 0 e {limite}.")
    return valor


class Banco:
    def __init__(self, caminho):
        self.conexao = sqlite3.connect(caminho)
        self.conexao.row_factory = sqlite3.Row
        self.conexao.execute("PRAGMA foreign_keys = ON")
        campos = ",\n".join(
            f"{coluna} REAL CHECK ({coluna} BETWEEN 0 AND {AVALIACOES[i % 5][1]})"
            for i, coluna in enumerate(COLUNAS)
        )
        self.conexao.executescript(f"""
            CREATE TABLE IF NOT EXISTS diarios (
                id INTEGER PRIMARY KEY,
                escola TEXT NOT NULL,
                professor TEXT NOT NULL,
                disciplina TEXT NOT NULL,
                turma TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alunos (
                id INTEGER PRIMARY KEY,
                diario_id INTEGER NOT NULL REFERENCES diarios(id) ON DELETE CASCADE,
                numero INTEGER NOT NULL CHECK (numero > 0),
                nome TEXT NOT NULL,
                {campos},
                UNIQUE (diario_id, numero)
            );
        """)

    def diarios(self):
        return self.conexao.execute(
            "SELECT * FROM diarios ORDER BY escola, turma, disciplina, professor, id"
        ).fetchall()

    def alunos(self, diario):
        return self.conexao.execute(
            "SELECT * FROM alunos WHERE diario_id = ? ORDER BY numero", (diario,)
        ).fetchall()

    def salvar_diario(self, registro, valores):
        with self.conexao:
            if registro is None:
                return self.conexao.execute(
                    "INSERT INTO diarios (escola, professor, disciplina, turma) VALUES (?, ?, ?, ?)",
                    valores,
                ).lastrowid
            self.conexao.execute(
                "UPDATE diarios SET escola = ?, professor = ?, disciplina = ?, turma = ? WHERE id = ?",
                (*valores, registro),
            )
        return registro

    def salvar_aluno(self, diario, registro, numero, nome, notas):
        campos = ("numero", "nome", *COLUNAS)
        valores = (numero, nome, *notas)
        with self.conexao:
            if registro is None:
                marcadores = ", ".join("?" for _ in range(len(campos) + 1))
                return self.conexao.execute(
                    f"INSERT INTO alunos (diario_id, {', '.join(campos)}) VALUES ({marcadores})",
                    (diario, *valores),
                ).lastrowid
            atribuicoes = ", ".join(f"{campo} = ?" for campo in campos)
            self.conexao.execute(
                f"UPDATE alunos SET {atribuicoes} WHERE id = ? AND diario_id = ?",
                (*valores, registro, diario),
            )
        return registro

    def excluir_diario(self, registro):
        with self.conexao:
            self.conexao.execute("DELETE FROM diarios WHERE id = ?", (registro,))

    def excluir_aluno(self, registro):
        with self.conexao:
            self.conexao.execute("DELETE FROM alunos WHERE id = ?", (registro,))


class Formulario(tk.Toplevel):
    def __init__(self, janela, titulo):
        super().__init__(janela)
        self.title(titulo)
        self.transient(janela)
        self.resizable(False, False)
        self.bind("<Escape>", lambda evento: self.destroy())
        self.corpo = ttk.Frame(self, padding=20)
        self.corpo.pack(fill="both", expand=True)
        self.grab_set()

    def campo(self, quadro, linha, rotulo, valor="", largura=30):
        ttk.Label(quadro, text=rotulo).grid(row=linha, column=0, sticky="w", padx=(0, 12), pady=4)
        entrada = ttk.Entry(quadro, width=largura)
        entrada.insert(0, valor)
        entrada.grid(row=linha, column=1, sticky="ew", pady=4)
        return entrada

    def acoes(self, salvar):
        quadro = ttk.Frame(self.corpo, padding=(0, 16, 0, 0))
        quadro.pack(fill="x")
        ttk.Button(quadro, text="Salvar", command=salvar).pack(side="right")
        ttk.Button(quadro, text="Cancelar", command=self.destroy).pack(side="right", padx=8)


class Aplicativo:
    def __init__(self, janela, banco):
        self.janela = janela
        self.banco = banco
        janela.title("Diário escolar")
        janela.geometry("960x550")
        janela.minsize(780, 420)
        estilo = ttk.Style(janela)
        estilo.configure("Treeview", rowheight=30)
        estilo.configure("Titulo.TLabel", font=("TkDefaultFont", 22, "bold"))

        corpo = ttk.Frame(janela, padding=24)
        corpo.pack(fill="both", expand=True)
        ttk.Label(corpo, text="Diário escolar", style="Titulo.TLabel").pack(anchor="w", pady=(0, 16))
        diarios = ttk.Frame(corpo)
        diarios.pack(fill="x", pady=(0, 18))
        ttk.Label(diarios, text="Diário").pack(side="left")
        self.seletor = ttk.Combobox(diarios, state="readonly")
        self.seletor.pack(side="left", fill="x", expand=True, padx=8)
        self.seletor.bind("<<ComboboxSelected>>", lambda evento: self.carregar_alunos())
        self.botao(diarios, "Novo", self.form_diario)
        self.editar_diario = self.botao(diarios, "Editar", lambda: self.form_diario(self.diario()))
        self.remover_diario = self.botao(diarios, "Excluir", self.excluir_diario)

        alunos = ttk.Frame(corpo)
        alunos.pack(fill="x", pady=(0, 8))
        self.contagem = ttk.Label(alunos)
        self.contagem.pack(side="left")
        self.novo_aluno = self.botao(alunos, "Cadastrar aluno", self.form_aluno)
        self.editar_aluno = self.botao(alunos, "Editar aluno e notas", self.editar_selecionado)
        self.remover_aluno = self.botao(alunos, "Excluir aluno", self.excluir_aluno)

        tabela = ttk.Frame(corpo)
        tabela.pack(fill="both", expand=True)
        titulos = ("Nº", "Nome do aluno", "1º trimestre", "2º trimestre", "3º trimestre", "Média final")
        self.lista = ttk.Treeview(tabela, columns=titulos, show="headings", selectmode="browse")
        for titulo, largura in zip(titulos, (55, 235, 95, 95, 95, 95)):
            self.lista.heading(titulo, text=titulo)
            self.lista.column(titulo, width=largura, stretch=titulo == "Nome do aluno",
                              anchor="w" if titulo == "Nome do aluno" else "center")
        barra = ttk.Scrollbar(tabela, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.lista.pack(fill="both", expand=True)
        self.lista.bind("<<TreeviewSelect>>", lambda evento: self.atualizar_botoes())
        self.lista.bind("<Double-1>", self.abrir_linha)
        self.carregar_diarios()

    @staticmethod
    def botao(quadro, texto, acao):
        botao = ttk.Button(quadro, text=texto, command=acao)
        botao.pack(side="left", padx=(4, 0))
        return botao

    def diario(self):
        indice = self.seletor.current()
        return self.registros_diarios[indice] if indice >= 0 else None

    def aluno(self):
        selecao = self.lista.selection()
        return self.registros_alunos.get(selecao[0]) if selecao else None

    def carregar_diarios(self, selecionar=None):
        self.registros_diarios = self.banco.diarios()
        self.seletor.configure(values=[
            f"{d['escola']} · {d['turma']} · {d['disciplina']} · {d['professor']} (#{d['id']})"
            for d in self.registros_diarios
        ])
        if self.registros_diarios:
            indice = next((i for i, d in enumerate(self.registros_diarios) if d["id"] == selecionar), 0)
            self.seletor.current(indice)
        else:
            self.seletor.set("")
        self.carregar_alunos()

    def carregar_alunos(self, selecionar=None):
        diario = self.diario()
        self.lista.delete(*self.lista.get_children())
        alunos = self.banco.alunos(diario["id"]) if diario else []
        self.registros_alunos = {str(aluno["id"]): aluno for aluno in alunos}
        for chave, aluno in self.registros_alunos.items():
            trimestres, final = calcular([aluno[campo] for campo in COLUNAS])
            valores = (aluno["numero"], aluno["nome"], *(formatar(t[3]) for t in trimestres), formatar(final))
            self.lista.insert("", "end", iid=chave, values=valores)
        if str(selecionar) in self.registros_alunos:
            self.lista.selection_set(str(selecionar))
            self.lista.see(str(selecionar))
        quantidade = len(alunos)
        texto = f"{quantidade} aluno" if quantidade == 1 else f"{quantidade} alunos"
        self.contagem.configure(text=texto if diario else "Crie um diário para cadastrar alunos.")
        self.atualizar_botoes()

    def atualizar_botoes(self):
        for botao in (self.editar_diario, self.remover_diario, self.novo_aluno):
            botao.state(["!disabled"] if self.diario() else ["disabled"])
        for botao in (self.editar_aluno, self.remover_aluno):
            botao.state(["!disabled"] if self.aluno() else ["disabled"])

    def form_diario(self, registro=None):
        form = Formulario(self.janela, "Editar diário" if registro else "Novo diário")
        quadro = ttk.Frame(form.corpo)
        quadro.pack(fill="x")
        chaves = ("escola", "professor", "disciplina", "turma")
        entradas = [
            form.campo(quadro, i, rotulo, registro[chave] if registro else "")
            for i, (chave, rotulo) in enumerate(zip(chaves, IDENTIFICACAO))
        ]

        def salvar():
            valores = tuple(entrada.get().strip() for entrada in entradas)
            if not all(valores):
                messagebox.showerror("Campos obrigatórios", "Preencha escola, professor, disciplina e turma.", parent=form)
                return
            diario = self.banco.salvar_diario(registro["id"] if registro else None, valores)
            form.destroy()
            self.carregar_diarios(diario)

        form.acoes(salvar)
        entradas[0].focus_set()

    def editar_selecionado(self):
        aluno = self.aluno()
        if aluno:
            self.form_aluno(aluno)

    def abrir_linha(self, evento):
        registro = self.lista.identify_row(evento.y)
        if registro:
            self.form_aluno(self.registros_alunos[registro])

    def form_aluno(self, registro=None):
        diario = self.diario()
        if diario is None:
            return
        form = Formulario(self.janela, "Editar aluno e notas" if registro else "Cadastrar aluno")
        dados = ttk.Frame(form.corpo)
        dados.pack(fill="x", pady=(0, 10))
        numero = form.campo(dados, 0, "Nº na turma", registro["numero"] if registro else "")
        nome = form.campo(dados, 1, "Nome do aluno", registro["nome"] if registro else "", 44)

        abas = ttk.Notebook(form.corpo)
        abas.pack(fill="x")
        notas = []
        resumos = []

        def atualizar_resumo(evento=None):
            for resumo in resumos:
                resumo.configure(text="")
            final.configure(text="")
            try:
                valores = [ler_nota(campo.get(), AVALIACOES[i % 5][1]) for i, campo in enumerate(notas)]
            except ValueError:
                final.configure(text="Confira os limites das notas digitadas.")
                return
            trimestres, resultado = calcular(valores)
            for resumo, (n1, n2, n3, trimestre) in zip(resumos, trimestres):
                resumo.configure(text=f"N1  {formatar(n1)}    N2  {formatar(n2)}    N3  {formatar(n3)}"
                                      f"    Média  {formatar(trimestre)}")
            final.configure(text=f"Média final  {formatar(resultado)}")

        for tri in range(3):
            quadro = ttk.Frame(abas, padding=12)
            abas.add(quadro, text=f"{tri + 1}º trimestre")
            for i, (rotulo, limite) in enumerate(AVALIACOES):
                valor = registro[COLUNAS[tri * 5 + i]] if registro else None
                texto = "" if valor is None else str(valor).replace(".", ",")
                campo = form.campo(quadro, i, f"{rotulo} (até {limite})", texto, 12)
                campo.bind("<KeyRelease>", atualizar_resumo)
                notas.append(campo)
            resumo = ttk.Label(quadro, padding=(0, 10, 0, 0))
            resumo.grid(row=5, column=0, columnspan=2, sticky="w")
            resumos.append(resumo)

        final = ttk.Label(form.corpo, padding=(0, 10, 0, 0))
        final.pack(anchor="w")
        atualizar_resumo()

        def salvar():
            try:
                chamada = int(numero.get())
                if not 1 <= chamada <= 2**63 - 1:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Número inválido", "Informe um número inteiro positivo para o aluno.", parent=form)
                numero.focus_set()
                return
            nome_aluno = nome.get().strip()
            if not nome_aluno:
                messagebox.showerror("Nome obrigatório", "Informe o nome do aluno.", parent=form)
                nome.focus_set()
                return
            valores = []
            for i, campo in enumerate(notas):
                rotulo, limite = AVALIACOES[i % 5]
                try:
                    valores.append(ler_nota(campo.get(), limite))
                except ValueError as erro:
                    abas.select(i // 5)
                    messagebox.showerror("Nota inválida", f"{i // 5 + 1}º trimestre · {rotulo}\n{erro}", parent=form)
                    campo.focus_set()
                    return
            try:
                aluno = self.banco.salvar_aluno(diario["id"], registro["id"] if registro else None,
                                               chamada, nome_aluno, valores)
            except sqlite3.IntegrityError:
                messagebox.showerror("Número em uso", "Já existe um aluno com esse número neste diário.", parent=form)
                return
            form.destroy()
            self.carregar_alunos(aluno)

        form.acoes(salvar)
        numero.focus_set()

    def excluir_diario(self):
        diario = self.diario()
        if diario and messagebox.askyesno(
            "Excluir diário",
            f"Excluir o diário de {diario['disciplina']} da turma {diario['turma']} e todos os alunos e notas dele?",
            parent=self.janela,
        ):
            self.banco.excluir_diario(diario["id"])
            self.carregar_diarios()

    def excluir_aluno(self):
        aluno = self.aluno()
        if aluno and messagebox.askyesno(
            "Excluir aluno", f"Excluir {aluno['nome']} e suas notas deste diário?", parent=self.janela,
        ):
            self.banco.excluir_aluno(aluno["id"])
            self.carregar_alunos()


def main():
    caminho = Path(__file__).resolve().with_name("escola.sqlite3")
    banco = Banco(caminho)
    with closing(banco.conexao):
        janela = tk.Tk()
        Aplicativo(janela, banco)
        janela.mainloop()


if __name__ == "__main__":
    main()
