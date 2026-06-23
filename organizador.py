import os
import tkinter as tk
from tkinter import messagebox


def listar_archivos(ruta_carpeta, texto_salida):
    """Función que lee y muestra los archivos dentro de una ruta específica."""
    texto_salida.config(state="normal")
    texto_salida.delete("1.0", tk.END)

    if os.path.exists(ruta_carpeta):
        texto_salida.insert(tk.END, f"✅ Conexión exitosa. Leyendo la ruta...: {ruta_carpeta}\n\n")
        elementos = os.listdir(ruta_carpeta)

        if not elementos:
            texto_salida.insert(tk.END, "⚠️ La carpeta está vacía.\n")
        else:
            texto_salida.insert(tk.END, "--- Archivos encontrados ---\n")
            for elemento in elementos:
                texto_salida.insert(tk.END, f"- {elemento}\n")
    else:
        messagebox.showerror("Error de ruta", f"La ruta '{ruta_carpeta}' no existe. Verifica que esté bien escrita.")

    texto_salida.config(state="disabled")


def buscar_por_nombre(ruta_carpeta, termino, texto_salida):
    """Busca archivos y carpetas cuyo nombre contenga el término especificado."""
    texto_salida.config(state="normal")
    texto_salida.delete("1.0", tk.END)

    ruta_carpeta = ruta_carpeta.strip()
    termino = termino.strip().lower()

    if not ruta_carpeta:
        messagebox.showwarning("Ruta vacía", "Ingresa una ruta válida para buscar.")
        texto_salida.config(state="disabled")
        return

    if not os.path.exists(ruta_carpeta):
        messagebox.showerror("Error de ruta", f"La ruta '{ruta_carpeta}' no existe. Verifica que esté bien escrita.")
        texto_salida.config(state="disabled")
        return

    if not termino:
        messagebox.showinfo("Sin término", "Ingresa un texto para buscar por nombre.")
        texto_salida.config(state="disabled")
        return

    texto_salida.insert(tk.END, f"🔎 Buscando '{termino}' en {ruta_carpeta}...\n\n")
    coincidencias = []

    for raiz, dirs, archivos in os.walk(ruta_carpeta):
        for nombre in dirs + archivos:
            if termino in nombre.lower():
                ruta_relativa = os.path.relpath(os.path.join(raiz, nombre), ruta_carpeta)
                tipo = "Carpeta" if nombre in dirs else "Archivo"
                coincidencias.append((tipo, ruta_relativa))

    if not coincidencias:
        texto_salida.insert(tk.END, "❌ No se encontraron archivos o carpetas con ese nombre.\n")
    else:
        texto_salida.insert(tk.END, f"--- {len(coincidencias)} coincidencia(s) encontradas ---\n")
        for tipo, ruta in coincidencias:
            texto_salida.insert(tk.END, f"[{tipo}] {ruta}\n")

    texto_salida.config(state="disabled")


if __name__ == "__main__":
    ventana = tk.Tk()
    ventana.title("Organizador de Archivos")
    ventana.geometry("660x460")
    ventana.resizable(False, False)

    etiqueta_ruta = tk.Label(ventana, text="Ruta de carpeta:", font=("Segoe UI", 11))
    etiqueta_ruta.pack(pady=(20, 4), padx=20, anchor="w")

    entrada_ruta = tk.Entry(ventana, width=80, font=("Segoe UI", 10))
    entrada_ruta.pack(padx=20)

    etiqueta_busqueda = tk.Label(ventana, text="Buscar por nombre (texto parcial):", font=("Segoe UI", 11))
    etiqueta_busqueda.pack(pady=(16, 4), padx=20, anchor="w")

    entrada_busqueda = tk.Entry(ventana, width=80, font=("Segoe UI", 10))
    entrada_busqueda.pack(padx=20)

    boton_frame = tk.Frame(ventana)
    boton_frame.pack(pady=14)

    boton_listar = tk.Button(
        boton_frame,
        text="Listar carpeta",
        font=("Segoe UI", 10, "bold"),
        command=lambda: listar_archivos(entrada_ruta.get().strip(), texto_salida),
        bg="#4CAF50",
        fg="white",
        activebackground="#45A049",
        padx=14,
        pady=8,
    )
    boton_listar.grid(row=0, column=0, padx=6)

    boton_buscar = tk.Button(
        boton_frame,
        text="Buscar por nombre",
        font=("Segoe UI", 10, "bold"),
        command=lambda: buscar_por_nombre(entrada_ruta.get().strip(), entrada_busqueda.get().strip(), texto_salida),
        bg="#2196F3",
        fg="white",
        activebackground="#1976D2",
        padx=14,
        pady=8,
    )
    boton_buscar.grid(row=0, column=1, padx=6)

    texto_salida = tk.Text(ventana, width=78, height=18, font=("Consolas", 10), state="disabled", wrap="word")
    texto_salida.pack(padx=20, pady=(0, 20))

    scrollbar = tk.Scrollbar(ventana, command=texto_salida.yview)
    texto_salida.config(yscrollcommand=scrollbar.set)
    scrollbar.place(relx=0.975, rely=0.255, relheight=0.60)

    ventana.mainloop()