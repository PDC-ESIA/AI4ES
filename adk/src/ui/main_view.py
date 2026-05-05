import tkinter as tk

class MainView:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('hello world')
        self.root.configure(bg='white')
        self._configure_window()
        self._add_centered_label()

    def _configure_window(self):
        self.root.geometry('400x200')  # Tamanho padrão
        self.root.resizable(False, False)  # Janela fixa

    def _add_centered_label(self):
        label = tk.Label(
            self.root, 
            text='hello world', 
            font=('Helvetica', 24), 
            fg='black',
            bg='white',
            bd=0,
            highlightthickness=0
        )
        label.place(relx=0.5, rely=0.5, anchor='center')
