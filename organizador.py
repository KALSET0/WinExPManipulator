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


def abrir_elemento(ruta, entrada_ruta, texto_salida):
    """Abre una carpeta en la interfaz, si es archivo, en la app predeterminada."""
    if not ruta:
        messagebox.showwarning("Ruta vacía", "Ingresa la ruta del elemento a abrir.")
        return
    
    # Si la ruta es relativa, combinarla con la ruta base
    if not os.path.isabs(ruta):
        ruta_base = entrada_ruta.get().strip()
        ruta_completa = os.path.join(ruta_base, ruta) if ruta_base else ruta
    else:
        ruta_completa = ruta
    
    # Convertir a ruta absoluta si aún no lo es
    ruta_completa = os.path.abspath(ruta_completa)
    
    if not os.path.exists(ruta_completa):
        messagebox.showerror("Ruta no encontrada", f"La ruta '{ruta_completa}' no existe.")
        return
    
    try:
        # Si es una carpeta, cargarla en la interfaz
        if os.path.isdir(ruta_completa):
            entrada_ruta.delete(0, tk.END)
            entrada_ruta.insert(0, ruta_completa)
            listar_archivos(ruta_completa, texto_salida)
        else:
            # Si es un archivo, abrirlo con la aplicación predeterminada
            os.startfile(ruta_completa)
            messagebox.showinfo("Éxito", f"Abriendo archivo: {ruta_completa}")
    except Exception as e:
        messagebox.showerror("Error al abrir", f"No se pudo abrir el elemento: {str(e)}")


def renombrar_elemento(ruta):
    """Placeholder para renombrar un archivo o carpeta."""
    if not ruta:
        messagebox.showwarning("Ruta vacía", "Ingresa la ruta del elemento a renombrar.")
        return
    messagebox.showinfo("Función pendiente", f"Renombrar: {ruta}")


def eliminar_elemento(ruta):
    """Placeholder para eliminar un archivo o carpeta."""
    if not ruta:
        messagebox.showwarning("Ruta vacía", "Ingresa la ruta del elemento a eliminar.")
        return
    messagebox.showinfo("Función pendiente", f"Eliminar: {ruta}")


def copiar_elemento(ruta):
    """Placeholder para copiar un archivo o carpeta."""
    if not ruta:
        messagebox.showwarning("Ruta vacía", "Ingresa la ruta del elemento a copiar.")
        return
    messagebox.showinfo("Función pendiente", f"Copiar: {ruta}")


def cortar_elemento(ruta):
    """Placeholder para cortar un archivo o carpeta."""
    if not ruta:
        messagebox.showwarning("Ruta vacía", "Ingresa la ruta del elemento a cortar.")
        return
    messagebox.showinfo("Función pendiente", f"Cortar: {ruta}")


def pegar_elemento(ruta):
    """Placeholder para pegar el elemento copiado o cortado."""
    if not ruta:
        messagebox.showwarning("Ruta vacía", "Ingresa la ruta de destino para pegar.")
        return
    messagebox.showinfo("Función pendiente", f"Pegar en: {ruta}")


if __name__ == "__main__":
    ventana = tk.Tk()
    ventana.title("Organizador de Archivos")
    ventana.geometry("660x750")
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

    etiqueta_seleccion = tk.Label(ventana, text="Ruta seleccionada:", font=("Segoe UI", 11))
    etiqueta_seleccion.pack(pady=(10, 4), padx=20, anchor="w")

    entrada_seleccion = tk.Entry(ventana, width=80, font=("Segoe UI", 10))
    entrada_seleccion.pack(padx=20)

    acciones_frame = tk.Frame(ventana)
    acciones_frame.pack(pady=10)

    boton_abrir = tk.Button(
        acciones_frame,
        text="Abrir",
        font=("Segoe UI", 10),
        command=lambda: abrir_elemento(entrada_seleccion.get().strip(), entrada_ruta, texto_salida),
        bg="#607D8B",
        fg="white",
        activebackground="#546E7A",
        padx=12,
        pady=6,
    )
    boton_abrir.grid(row=0, column=0, padx=4, pady=4)

    boton_renombrar = tk.Button(
        acciones_frame,
        text="Renombrar",
        font=("Segoe UI", 10),
        command=lambda: renombrar_elemento(entrada_seleccion.get().strip()),
        bg="#795548",
        fg="white",
        activebackground="#6D4C41",
        padx=12,
        pady=6,
    )
    boton_renombrar.grid(row=0, column=1, padx=4, pady=4)

    boton_eliminar = tk.Button(
        acciones_frame,
        text="Eliminar",
        font=("Segoe UI", 10),
        command=lambda: eliminar_elemento(entrada_seleccion.get().strip()),
        bg="#D32F2F",
        fg="white",
        activebackground="#C62828",
        padx=12,
        pady=6,
    )
    boton_eliminar.grid(row=0, column=2, padx=4, pady=4)

    boton_copiar = tk.Button(
        acciones_frame,
        text="Copiar",
        font=("Segoe UI", 10),
        command=lambda: copiar_elemento(entrada_seleccion.get().strip()),
        bg="#1976D2",
        fg="white",
        activebackground="#1565C0",
        padx=12,
        pady=6,
    )
    boton_copiar.grid(row=1, column=0, padx=4, pady=4)

    boton_cortar = tk.Button(
        acciones_frame,
        text="Cortar",
        font=("Segoe UI", 10),
        command=lambda: cortar_elemento(entrada_seleccion.get().strip()),
        bg="#FBC02D",
        fg="black",
        activebackground="#F9A825",
        padx=12,
        pady=6,
    )
    boton_cortar.grid(row=1, column=1, padx=4, pady=4)

    boton_pegar = tk.Button(
        acciones_frame,
        text="Pegar",
        font=("Segoe UI", 10),
        command=lambda: pegar_elemento(entrada_seleccion.get().strip()),
        bg="#388E3C",
        fg="white",
        activebackground="#2E7D32",
        padx=12,
        pady=6,
    )
    boton_pegar.grid(row=1, column=2, padx=4, pady=4)

    texto_salida = tk.Text(ventana, width=78, height=14, font=("Consolas", 10), state="disabled", wrap="word")
    texto_salida.pack(padx=20, pady=(0, 10))

    scrollbar = tk.Scrollbar(ventana, command=texto_salida.yview)
    texto_salida.config(yscrollcommand=scrollbar.set)
    scrollbar.place(relx=0.975, rely=0.28, relheight=0.56)

    ventana.mainloop()

