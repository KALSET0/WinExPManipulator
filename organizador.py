import os
import re
import tkinter as tk
from tkinter import messagebox, ttk
import threading
from queue import Queue


def buscar_en_hilo(ruta_acceso, termino, cola_actualizacion, cola_resultados):
    """Ejecuta la búsqueda en un hilo secundario."""
    try:
        # Primera pasada: contar archivos totales
        total_elementos = 0
        for raiz, dirs, archivos in os.walk(ruta_acceso):
            total_elementos += len(dirs) + len(archivos)

        cola_actualizacion.put(("total", total_elementos))
        coincidencias = []
        contador = 0

        # Segunda pasada: buscar y actualizar progreso
        for raiz, dirs, archivos in os.walk(ruta_acceso):
            for nombre in dirs + archivos:
                contador += 1
                cola_actualizacion.put(("progreso", contador))

                nombre_minusculas = nombre.lower()
                # Sí permite un pequeño prefijo y sufijo, pero rechaza palabras muy largas.
                termino_regex = re.escape(termino)
                if re.search(rf"(?:(?<![a-z0-9])[a-z0-9]{{0,3}}){termino_regex}[a-z0-9]{{0,5}}(?![a-z0-9])", nombre_minusculas):
                    ruta_relativa = os.path.relpath(os.path.join(raiz, nombre), ruta_acceso)
                    tipo = "Carpeta" if nombre in dirs else "Archivo"
                    coincidencias.append((tipo, ruta_relativa))

        cola_resultados.put(coincidencias)
    except Exception as e:
        cola_resultados.put(("error", str(e)))


def monitorear_cola(ventana, cola_actualizacion, cola_resultados, barra_progreso, texto_salida, hilo):
    """Monitorea las colas y actualiza la GUI desde el hilo principal."""
    # Procesa todas las actualizaciones disponibles
    while not cola_actualizacion.empty():
        tipo, valor = cola_actualizacion.get()
        if tipo == "total":
            barra_progreso['maximum'] = max(1, valor)
        elif tipo == "progreso":
            barra_progreso['value'] = valor

    # Si el hilo aún está activo, revisa de nuevo en 100 ms
    if hilo.is_alive():
        ventana.after(100, lambda: monitorear_cola(ventana, cola_actualizacion, cola_resultados, barra_progreso, texto_salida, hilo))
    else:
        # El hilo terminó, obtén los resultados finales
        if not cola_resultados.empty():
            resultado = cola_resultados.get()
            
            # Verifica si hay un error
            if isinstance(resultado, tuple) and resultado[0] == "error":
                messagebox.showerror("Error de búsqueda", f"Ocurrió un error: {resultado[1]}")
                texto_salida.config(state="normal")
                texto_salida.insert(tk.END, f"❌ Error: {resultado[1]}")
                texto_salida.config(state="disabled")
            else:
                # Muestra los resultados
                coincidencias = resultado
                texto_salida.config(state="normal")
                if not coincidencias:
                    texto_salida.insert(tk.END, "❌ No se encontraron archivos o carpetas con ese nombre.\n")
                else:
                    texto_salida.insert(tk.END, f"--- {len(coincidencias)} coincidencia(s) encontradas ---\n")
                    for tipo, ruta in coincidencias:
                        texto_salida.insert(tk.END, f"[{tipo}] {ruta}\n")
                texto_salida.config(state="disabled")
            
            barra_progreso['value'] = barra_progreso['maximum']


def listar_archivos(ruta_acceso, texto_salida):
    """Función que lee y muestra los archivos dentro de una ruta específica."""
    texto_salida.config(state="normal")
    texto_salida.delete("1.0", tk.END)

    if os.path.exists(ruta_acceso):
        texto_salida.insert(tk.END, f"✅ Conexión exitosa. Leyendo la ruta...: {ruta_acceso}\n\n")
        elementos = os.listdir(ruta_acceso)

        if not elementos:
            texto_salida.insert(tk.END, "⚠️ La carpeta está vacía.\n")
        else:
            texto_salida.insert(tk.END, "--- Archivos encontrados ---\n")
            for elemento in elementos:
                texto_salida.insert(tk.END, f"- {elemento}\n")
    else:
        messagebox.showerror("Error de ruta", f"La ruta '{ruta_acceso}' no existe. Verifica que esté bien escrita.")

    texto_salida.config(state="disabled")


def buscar_por_nombre(ruta_acceso, termino, texto_salida, barra_progreso):
    """Busca archivos y carpetas usando un hilo secundario."""
    texto_salida.config(state="normal")
    texto_salida.delete("1.0", tk.END)
    barra_progreso['value'] = 0

    ruta_acceso = ruta_acceso.strip()
    termino = termino.strip().lower()

    if not ruta_acceso:
        messagebox.showwarning("Ruta vacía", "Ingresa una ruta válida para buscar.")
        texto_salida.config(state="disabled")
        barra_progreso['value'] = 0
        return

    if not os.path.exists(ruta_acceso):
        messagebox.showerror("Error de ruta", f"La ruta '{ruta_acceso}' no existe. Verifica que esté bien escrita.")
        texto_salida.config(state="disabled")
        barra_progreso['value'] = 0
        return

    if not termino:
        messagebox.showinfo("Sin término", "Ingresa un texto para buscar por nombre.")
        texto_salida.config(state="disabled")
        barra_progreso['value'] = 0
        return

    texto_salida.insert(tk.END, f"🔎 Buscando '{termino}' en {ruta_acceso}...\n\n")
    texto_salida.config(state="disabled")

    # Crear colas para comunicación entre hilos
    cola_actualizacion = Queue()
    cola_resultados = Queue()

    # Iniciar hilo secundario
    hilo = threading.Thread(target=buscar_en_hilo, args=(ruta_acceso, termino, cola_actualizacion, cola_resultados))
    hilo.start()

    # Iniciar monitoreo desde el hilo principal
    ventana = texto_salida.winfo_toplevel()
    monitorear_cola(ventana, cola_actualizacion, cola_resultados, barra_progreso, texto_salida, hilo)


if __name__ == "__main__":
    ventana = tk.Tk()
    ventana.title("Organizador de Archivos")
    ventana.geometry("660x500")
    ventana.resizable(False, False)

    etiqueta_ruta = tk.Label(ventana, text="Ruta de acceso:", font=("Segoe UI", 11))
    etiqueta_ruta.pack(pady=(20, 4), padx=20, anchor="w")

    entrada_ruta = tk.Entry(ventana, width=80, font=("Segoe UI", 10))
    entrada_ruta.pack(padx=20)

    etiqueta_busqueda = tk.Label(ventana, text="Buscar por nombre:", font=("Segoe UI", 11))
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
        command=lambda: buscar_por_nombre(entrada_ruta.get().strip(), entrada_busqueda.get().strip(), texto_salida, barra_progreso),
        bg="#2196F3",
        fg="white",
        activebackground="#1976D2",
        padx=14,
        pady=8,
    )
    boton_buscar.grid(row=0, column=1, padx=6)

    barra_progreso = ttk.Progressbar(ventana, mode='determinate', length=600)
    barra_progreso.pack(padx=20, pady=(10, 8), fill=tk.X)

    texto_salida = tk.Text(ventana, width=78, height=14, font=("Consolas", 10), state="disabled", wrap="word")
    texto_salida.pack(padx=20, pady=(0, 10))

    scrollbar = tk.Scrollbar(ventana, command=texto_salida.yview)
    texto_salida.config(yscrollcommand=scrollbar.set)
    scrollbar.place(relx=0.975, rely=0.28, relheight=0.56)

    ventana.mainloop()

