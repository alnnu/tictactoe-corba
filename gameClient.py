#!/usr/bin/env python3

# gameClient.py

import sys
import threading
import CORBA
import PortableServer
import TicTacToe, TicTacToe__POA

from tkinter import *
from tkinter import messagebox


class GameBrowser:
    """Interface gráfica principal para o cliente do jogo."""

    def __init__(self, orb, poa, gameFactory):
        self.orb = orb
        self.poa = poa
        self.gameFactory = gameFactory
        self.initGui()
        self.getGameList()
        print("GameBrowser inicializado")

    def initGui(self):
        """Inicializa a interface gráfica com Tkinter."""
        self.master = Tk()
        self.master.title("Cliente de Jogo")
        self.master.resizable(0, 0)

        frame = Frame(self.master)

        # Listbox com barra de rolagem
        listframe = Frame(frame)
        scrollbar = Scrollbar(listframe, orient=VERTICAL)
        self.listbox = Listbox(listframe, exportselection=0, width=30, height=20, yscrollcommand=scrollbar.set)

        scrollbar.config(command=self.listbox.yview)
        self.listbox.pack(side=LEFT, fill=BOTH, expand=1)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.listbox.bind("<ButtonRelease-1>", self.selectGame)
        listframe.grid(row=0, column=0, rowspan=6)

        # Espaçamento
        Frame(frame, width=20).grid(row=0, column=1, rowspan=6)

        # Botões
        buttons = [
            ("Novo Jogo", self.newGame),
            ("Entrar no Jogo", self.joinGame),
            ("Assistir Jogo", self.watchGame),
            ("Encerrar Jogo", self.killGame),
            ("Atualizar Lista", self.update),
            ("Sair", frame.quit),
        ]
        for i, (text, command) in enumerate(buttons):
            button = Button(frame, text=text, width=15, command=command)
            button.grid(row=i, column=2)

        self.newGameDialogue = None

        # Barra de status
        self.statusbar = Label(self.master, text="", bd=1, relief=SUNKEN, anchor=W)
        self.statusbar.pack(side=BOTTOM, fill=X)

        frame.pack(side=TOP)

    def getGameList(self):
        """Obtém a lista de jogos do GameFactory e atualiza o Listbox."""
        self.gameList = []
        self.listbox.delete(0, END)

        try:
            seq, iterator = self.gameFactory.listGames(0)
        except CORBA.SystemException as ex:
            print(f"Exceção do sistema ao acessar GameFactory: {CORBA.id(ex)}, {ex}")
            return

        if iterator is None:
            print("Nenhum jogo encontrado no GameFactory.")
            return

        try:
            more = True
            while more:
                seq, more = iterator.next_n(1)

                for info in seq:
                    self.gameList.append(info)
                    self.listbox.insert(END, info.name)

            iterator.destroy()

        except CORBA.SystemException as ex:
            print(f"Exceção do sistema ao acessar GameIterator: {CORBA.id(ex)}, {ex}")

    def statusMessage(self, msg):
        """Atualiza a barra de status."""
        self.statusbar.config(text=msg)

    def selectGame(self, evt):
        """Exibe informações do jogo selecionado."""
        selection = self.listbox.curselection()
        if not selection:
            return

        index = int(selection[0])
        info = self.gameList[index]

        try:
            players = info.obj._get_players()
            msg = (
                "sem jogadores" if players == 0 else
                "um jogador aguardando" if players == 1 else
                "jogo em andamento"
            )
        except CORBA.SystemException as ex:
            print(f"Erro ao acessar Game: {CORBA.id(ex)}, {ex}")
            msg = "Erro ao acessar o jogo"

        self.statusMessage(f"{info.name}: {msg}")

    def newGame(self):
        """Abre um diálogo para criar um novo jogo."""
        if self.newGameDialogue:
            self.newGameDialogue.destroy()

        self.newGameDialogue = Toplevel(self.master)
        self.newGameDialogue.transient()
        self.newGameDialogue.title("Novo Jogo")
        self.newGameDialogue.geometry(f"+{self.master.winfo_x()}+{self.master.winfo_y()}")

        Label(self.newGameDialogue, text="Digite o nome do novo jogo:").pack()

        entry = Entry(self.newGameDialogue)
        entry.pack()
        entry.focus()
        entry.bind("<Return>", self.newGameEntered)

    def newGameEntered(self, evt):
        """Cria o novo jogo com o nome inserido."""
        name = evt.widget.get()
        self.newGameDialogue.destroy()
        self.newGameDialogue = None

        if not name:
            self.statusMessage("Por favor, insira um nome válido para o jogo.")
            return

        try:
            self.gameFactory.newGame(name)
        except TicTacToe.GameFactory.NameInUse:
            self.statusMessage("Nome de jogo já em uso.")
        except CORBA.SystemException as ex:
            print(f"Erro ao criar jogo: {CORBA.id(ex)}, {ex}")
            self.statusMessage("Erro ao criar o jogo.")
        else:
            self.getGameList()

    def joinGame(self):
        """Entra no jogo selecionado."""
        selection = self.listbox.curselection()
        if not selection:
            return

        index = int(selection[0])
        info = self.gameList[index]

        try:
            controller, playerType = info.obj.joinGame(self.poa.create_reference())
            stype = "O" if playerType == TicTacToe.Nought else "X"
            self.statusMessage(f"Entrou no jogo {info.name} como {stype}.")
        except TicTacToe.Game.CannotJoin:
            self.statusMessage("Não foi possível entrar no jogo.")
        except CORBA.SystemException as ex:
            print(f"Erro ao entrar no jogo: {CORBA.id(ex)}, {ex}")
            self.statusMessage("Erro ao entrar no jogo.")

    def watchGame(self):
        """Assiste ao jogo selecionado."""
        # Similar ao joinGame, mas cria um Spectator_i.

    def update(self):
        """Atualiza a lista de jogos."""
        self.getGameList()

    def killGame(self):
        """Encerra o jogo selecionado."""
        selection = self.listbox.curselection()
        if not selection:
            return

        index = int(selection[0])
        info = self.gameList[index]

        try:
            info.obj.kill()
            self.statusMessage(f"Jogo {info.name} encerrado.")
        except CORBA.SystemException as ex:
            print(f"Erro ao encerrar o jogo: {CORBA.id(ex)}, {ex}")
            self.statusMessage("Erro ao encerrar o jogo.")
        finally:
            self.getGameList()