"""Caderno de ensino acessível pela Central; sem consultas ao modelo ou à rede."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit,
    QPushButton, QTabWidget, QVBoxLayout, QWidget)

from teaching import MAX_QUESTION, evaluate, evaluation_text


class TeachingDialog(QDialog):
    def __init__(self, root, parent=None):
        super().__init__(parent)
        self.root = Path(root)
        self.setWindowTitle("Ensinar a Yuna")
        self.resize(720, 660)
        self.setMinimumSize(550, 540)
        self.setStyleSheet("""
            QDialog, QWidget { background:#16151e; color:#eeeaf7; font-size:13px; }
            QLabel { background:transparent; }
            QPushButton { background:#302a43; border:1px solid #685485;
                border-radius:8px; padding:9px; }
            QPushButton:hover { background:#4a385e; }
            QLineEdit, QPlainTextEdit, QListWidget { background:#211d2c; color:#f6f2fc;
                border:1px solid #685485; border-radius:6px; padding:8px; }
            QTabBar::tab { background:#272132; padding:10px; }
            QTabBar::tab:selected { background:#594178; }
        """)
        layout = QVBoxLayout(self)
        title = QLabel("✦  Um caderno para aprender com você")
        title.setStyleSheet("font-size:21px; font-weight:600; color:#d8baff;")
        layout.addWidget(title)
        intro = QLabel("Ensine uma resposta revisada. Ela será consultada em perguntas relacionadas, "
                       "mesmo após reiniciar. Isso não altera os pesos do Qwen.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)
        editor = QWidget()
        box = QVBoxLayout(editor)
        last = QPushButton("Usar a última resposta de conversa")
        last.clicked.connect(self.use_last)
        box.addWidget(last)
        box.addWidget(QLabel("Pergunta ou situação"))
        self.question = QLineEdit()
        self.question.setMaxLength(MAX_QUESTION)
        self.question.setPlaceholderText("Ex.: Como gosto de estudar Python?")
        box.addWidget(self.question)
        box.addWidget(QLabel("Resposta correta — revise antes de salvar"))
        self.answer = QPlainTextEdit()
        self.answer.setPlaceholderText("Escreva a resposta que deseja ensinar, com um exemplo se ajudar.")
        box.addWidget(self.answer, 1)
        note = QLabel("A mesma pergunta atualiza a lição existente. Exemplos são dados de conversa; "
                      "não executam código nem concedem acesso ao computador. Não inclua senhas.")
        note.setWordWrap(True)
        box.addWidget(note)
        save = QPushButton("Salvar lição revisada")
        save.clicked.connect(self.save_lesson)
        box.addWidget(save)
        tabs.addTab(editor, "Ensinar")
        review = QWidget()
        box = QVBoxLayout(review)
        self.lessons = QListWidget()
        self.lessons.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        box.addWidget(self.lessons, 1)
        row = QHBoxLayout()
        for label, callback in (("Editar", self.edit_selected), ("Apagar", self.delete_selected),
                                ("Exportar selecionadas…", self.export_selected)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            row.addWidget(button)
        box.addLayout(row)
        info = QLabel("Use Ctrl para selecionar várias. A exportação cria um JSONL local só com as "
                      "lições selecionadas; não inclui conversas ou documentos. Nenhum upload é feito.")
        info.setWordWrap(True)
        box.addWidget(info)
        tabs.addTab(review, "Minhas lições")
        test = QWidget()
        box = QVBoxLayout(test)
        label = QLabel("Confira quais exemplos seriam consultados antes de perguntar ao modelo.")
        label.setWordWrap(True)
        box.addWidget(label)
        self.query = QLineEdit()
        self.query.setMaxLength(MAX_QUESTION)
        self.query.setPlaceholderText("Digite uma pergunta para testar a recuperação")
        box.addWidget(self.query)
        check = QPushButton("Consultar exemplos relacionados")
        check.clicked.connect(self.preview)
        box.addWidget(check)
        benchmark = QPushButton("Avaliar os guias do projeto")
        benchmark.clicked.connect(self.benchmark)
        box.addWidget(benchmark)
        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        box.addWidget(self.result, 1)
        tabs.addTab(test, "Testar")
        self.tabs = tabs
        self.status = QLabel("Lições guardadas somente neste computador.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        close = QPushButton("Fechar")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self.refresh()

    @contextmanager
    def memory(self):
        from yuna import Memory
        memory = Memory(self.root / "data" / "yuna.db")
        try:
            yield memory
        finally:
            memory.close()

    def attempt(self, action):
        try:
            action()
        except (ValueError, OSError, sqlite3.Error) as exc:
            self.status.setText("Não concluí a operação: " + str(exc))

    def refresh(self):
        def run():
            with self.memory() as memory:
                rows = memory.teaching.lessons()
            self.lessons.clear()
            for row in rows:
                item = QListWidgetItem(f'{row["id"]} · revisão {row["revision"]} · {row["question"]}')
                item.setData(Qt.ItemDataRole.UserRole, row)
                self.lessons.addItem(item)
        self.attempt(run)

    def selected(self):
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.lessons.selectedItems()]

    def save_lesson(self):
        def run():
            with self.memory() as memory:
                ident = memory.teaching.teach(self.question.text(), self.answer.toPlainText())
                memory.export()
            self.refresh()
            self.status.setText(f"Obrigada! Lição {ident} salva. Você pode conferir a recuperação na aba Testar.")
        self.attempt(run)

    def use_last(self):
        def run():
            with self.memory() as memory:
                pair = memory.teaching.last_answer()
            if not pair:
                raise ValueError("A última resposta não é uma conversa gerada pelo modelo. Preencha um exemplo acima.")
            if len(pair[0]) > MAX_QUESTION:
                raise ValueError("A pergunta anterior é muito longa. Escreva uma versão menor para a lição.")
            self.question.setText(pair[0])
            self.answer.setPlainText(pair[1])
            self.status.setText("Resposta carregada como rascunho. Corrija o texto e clique em Salvar lição revisada.")
        self.attempt(run)

    def edit_selected(self):
        rows = self.selected()
        if len(rows) != 1:
            self.status.setText("Selecione uma lição para editar.")
            return
        self.question.setText(rows[0]["question"])
        self.answer.setPlainText(rows[0]["answer"])
        self.tabs.setCurrentIndex(0)
        self.status.setText("Salvar com a mesma pergunta substitui esta lição. Outra pergunta cria uma nova.")

    def delete_selected(self):
        rows = self.selected()
        if not rows:
            self.status.setText("Selecione as lições que deseja apagar.")
            return
        if QMessageBox.question(self, "Apagar lições", f"Apagar {len(rows)} lição(ões) selecionada(s)?") != QMessageBox.StandardButton.Yes:
            return
        def run():
            with self.memory() as memory:
                for row in rows:
                    memory.teaching.forget(row["id"])
                memory.export()
            self.refresh()
            self.status.setText("Lições apagadas do caderno. Exportações anteriores continuam onde você as salvou.")
        self.attempt(run)

    def export_selected(self):
        rows = self.selected()
        if not rows:
            self.status.setText("Selecione as lições revisadas que deseja exportar.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar lições selecionadas", "licoes-revisadas.jsonl", "JSONL (*.jsonl)")
        if not path:
            return
        def run():
            with self.memory() as memory:
                count = memory.teaching.export_jsonl([row["id"] for row in rows], path)
            self.status.setText(f"Exportei {count} lição(ões) para {path}. Nenhum modelo foi treinado ou enviado.")
        self.attempt(run)

    def preview(self):
        def run():
            with self.memory() as memory:
                rows = memory.teaching.search(self.query.text())
            self.result.setPlainText("\n\n".join(
                f'{row["source"]} · {row["id"]}\n{row["question"]}\n{row["answer"]}' for row in rows)
                or "Nenhum exemplo suficientemente relacionado. A Yuna responderá sem usar o caderno.")
        self.attempt(run)

    def benchmark(self):
        def run():
            with self.memory() as memory:
                result = evaluate(memory.teaching)
            failures = "\n".join(f'• {r["query"]}: esperada {r["expected"]}, recuperada {r["actual"]}'
                                 for r in result["cases"] if not r["passed"])
            self.result.setPlainText(evaluation_text(result) + ("\n\nCasos a melhorar:\n" + failures if failures else ""))
        self.attempt(run)
