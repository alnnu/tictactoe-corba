
#!/usr/bin/env python

# gameClient.py

import sys
import threading
from tkinter import *
import CORBA
import PortableServer
import TicTacToe
import TicTacToe__POA


class GameBrowser:
    """This class implements a top-level user interface to the game
    player. It lists the games currently running in the GameFactory.
    The user can choose to create new games, and join, watch or kill
    existing games."""

    def __init__(self, orb, poa, gameFactory):
        self.orb = orb
        self.poa = poa
        self.gameFactory = gameFactory
        self.initGui()
        self.getGameList()
        print("GameBrowser initialized")

    def initGui(self):
        """Initialize the Tk objects for the GUI"""

        self.master = Tk()
        self.master.title("Game Client")
        self.master.resizable(0, 0)

        frame = Frame(self.master)

        # List box and scrollbar
        listframe = Frame(frame)
        scrollbar = Scrollbar(listframe, orient=VERTICAL)
        self.listbox = Listbox(
            listframe,
            exportselection=0,
            width=30,
            height=20,
            yscrollcommand=scrollbar.set,
        )

        scrollbar.config(command=self.listbox.yview)
        self.listbox.pack(side=LEFT, fill=BOTH, expand=1)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.listbox.bind("<ButtonRelease-1>", self.selectGame)

        listframe.grid(row=0, column=0, rowspan=6)

        # Padding
        Frame(frame, width=20).grid(row=0, column=1, rowspan=6)

        # Buttons
        newbutton = Button(frame, text="New game", command=self.newGame)
        joinbutton = Button(frame, text="Join game", command=self.joinGame)
        watchbutton = Button(frame, text="Watch game", command=self.watchGame)
        killbutton = Button(frame, text="Kill game", command=self.killGame)
        updatebutton = Button(frame, text="Update list", command=self.update)
        quitbutton = Button(frame, text="Quit", command=frame.quit)

        for button in [
            newbutton,
            joinbutton,
            watchbutton,
            killbutton,
            updatebutton,
            quitbutton,
        ]:
            button.config(width=15)

        self.newbutton = newbutton
        newbutton.bind("<ButtonRelease-1>", self.setNewButtonPosition)

        newbutton.grid(row=0, column=2)
        joinbutton.grid(row=1, column=2)
        watchbutton.grid(row=2, column=2)
        killbutton.grid(row=3, column=2)
        updatebutton.grid(row=4, column=2)
        quitbutton.grid(row=5, column=2)

        self.newGameDialogue = None

        # Padding at bottom
        Frame(frame, height=10).grid(row=6, columnspan=3)

        # Status bar
        self.statusbar = Label(self.master, text="", bd=1, relief=SUNKEN, anchor=W)
        self.statusbar.pack(side=BOTTOM, fill=X)

        frame.pack(side=TOP)

    def getGameList(self):
        """Get the list of games from the GameFactory, and populate
        the Listbox in the GUI"""

        self.gameList = []
        self.listbox.delete(0, END)

        try:
            seq, iterator = self.gameFactory.listGames(0)
        except CORBA.SystemException as ex:
            print("System exception contacting GameFactory:")
            print("  ", CORBA.id(ex), ex)
            return

        if len(seq) > 0:
            print("listGames() did not return an empty sequence as it should")

        if iterator is None:
            print("No games in the GameFactory")
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
            print("System exception contacting GameIterator:")
            print("  ", CORBA.id(ex), ex)

    def statusMessage(self, msg):
        self.statusbar.config(text=msg)

    def selectGame(self, evt):
        selection = self.listbox.curselection()

        if not selection:
            return

        index = int(selection[0])
        info = self.gameList[index]

        try:
            players = info.obj._get_players()
            if players == 0:
                msg = "No players yet"
            elif players == 1:
                msg = "One player waiting"
            else:
                msg = "Game in progress"

        except CORBA.SystemException as ex:
            print("System exception contacting Game:")
            print("  ", CORBA.id(ex), ex)
            msg = "Error contacting Game object"

        self.statusMessage(f"{info.name}: {msg}")

    def setNewButtonPosition(self, evt):
        self._new_x = self.master.winfo_x() + self.newbutton.winfo_x() + evt.x
        self._new_y = self.master.winfo_y() + self.newbutton.winfo_y() + evt.y

    def newGame(self):
        if self.newGameDialogue:
            self.newGameDialogue.destroy()

        self.newGameDialogue = toplevel = Toplevel(self.master)
        toplevel.transient()
        toplevel.title("New game...")
        toplevel.geometry(f"+{self._new_x}+{self._new_y}")

        Label(toplevel, text="Enter name for new game").pack()

        entry = Entry(toplevel)
        entry.pack()
        entry.focus()

        entry.bind("<Return>", self.newGameEntered)

    def newGameEntered(self, evt):
        name = evt.widget.get()
        self.newGameDialogue.destroy()
        self.newGameDialogue = None

        if not name:
            self.statusMessage("You must give a non-empty name")
            return

        try:
            self.gameFactory.newGame(name)

        except TicTacToe.GameFactory.NameInUse:
            self.statusMessage("Game name in use")
            return

        except CORBA.SystemException as ex:
            print("System exception trying to create new game:")
            print("  ", CORBA.id(ex), ex)
            self.statusMessage("System exception trying to create new game")
            return

        self.getGameList()

    def joinGame(self):
        # Resto do método joinGame aqui...

    def watchGame(self):
        # Método para assistir o jogo...

    def killGame(self):
        # Método para encerrar o jogo...

    def update(self):
        self.getGameList()