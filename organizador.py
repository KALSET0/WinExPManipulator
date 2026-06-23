import os
import re
import shutil
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import threading
from queue import Queue

#Variables globales para el portapapeles y el historial de rutas
copy_buffer = []
clipboard_action = None
ruta_historial = []
MOSTRAR_PC = "This PC"


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


def listar_archivos(ruta_acceso, texto_salida, listbox=None):
    """Función que lee y muestra los archivos dentro de una ruta específica."""
    if listbox is not None:
        listbox.delete(0, tk.END)

    texto_salida.config(state="normal")
    texto_salida.delete("1.0", tk.END)

    if os.path.exists(ruta_acceso):
        texto_salida.insert(tk.END, f"✅ Conexión exitosa. Leyendo la ruta...: {ruta_acceso}\n\n")
        elementos = sorted(os.listdir(ruta_acceso))

        if not elementos:
            texto_salida.insert(tk.END, "⚠️ La carpeta está vacía.\n")
        else:
            texto_salida.insert(tk.END, "--- Archivos encontrados ---\n")
            for elemento in elementos:
                texto_salida.insert(tk.END, f"- {elemento}\n")
                if listbox is not None:
                    listbox.insert(tk.END, elemento)
    else:
        if listbox is not None:
            listbox.delete(0, tk.END)
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


def obtener_unidades_windows():
    """Obtiene las unidades de disco disponibles."""
    try:
        import string
        drives = []
        bitmask = __import__('ctypes').windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if bitmask & (1 << i):
                letra = f"{string.ascii_uppercase[i]}:\\"
                drives.append(letra)
        return drives
    except Exception:
        return []


def mostrar_this_pc(texto_salida, listbox, entrada_ruta, agregar_al_historial=True):
    global ruta_historial
    """Muestra las unidades de disco disponibles en Windows."""
    if agregar_al_historial:
        ruta_actual = entrada_ruta.get().strip()
        if ruta_actual and ruta_actual != MOSTRAR_PC and os.path.exists(ruta_actual):
            ruta_historial.append(ruta_actual)

    entrada_ruta.delete(0, tk.END)
    entrada_ruta.insert(0, MOSTRAR_PC)

    texto_salida.config(state="normal")
    texto_salida.delete("1.0", tk.END)
    texto_salida.insert(tk.END, "--- This PC ---\n")
    texto_salida.config(state="disabled")

    listbox.delete(0, tk.END)
    for unidad in obtener_unidades_windows():
        listbox.insert(tk.END, unidad)


def cargar_ruta(ruta_acceso, entrada_ruta, texto_salida, listbox, agregar_al_historial=True):
    ruta_acceso = ruta_acceso.strip()
    """Carga y muestra el contenido de la ruta especificada."""
    if not ruta_acceso:
        mostrar_this_pc(texto_salida, listbox, entrada_ruta, agregar_al_historial)
        return

    if ruta_acceso == MOSTRAR_PC:
        mostrar_this_pc(texto_salida, listbox, entrada_ruta, agregar_al_historial)
        return

    if not os.path.exists(ruta_acceso):
        messagebox.showerror("Error de ruta", f"La ruta '{ruta_acceso}' no existe. Verifica que esté bien escrita.")
        return

    ruta_actual = entrada_ruta.get().strip()
    if agregar_al_historial and ruta_actual and ruta_actual != ruta_acceso and os.path.exists(ruta_actual):
        ruta_historial.append(ruta_actual)

    entrada_ruta.delete(0, tk.END)
    entrada_ruta.insert(0, ruta_acceso)
    listar_archivos(ruta_acceso, texto_salida, listbox)


def regresar_ruta_anterior(entrada_ruta, texto_salida, listbox):
    global ruta_historial
    """Regresa a la ruta anterior en el historial."""
    if not ruta_historial:
        messagebox.showinfo("Historial vacío", "No hay rutas anteriores para regresar.")
        return

    ruta_anterior = ruta_historial.pop()
    entrada_ruta.delete(0, tk.END)
    entrada_ruta.insert(0, ruta_anterior)
    listar_archivos(ruta_anterior, texto_salida, listbox)


def seleccionar_elementos(listbox, entrada_ruta):
    """Devuelve rutas absolutas seleccionadas en el listbox."""
    indices = listbox.curselection()
    if not indices:
        messagebox.showwarning("Selección vacía", "Selecciona al menos un elemento en la lista.")
        return []

    ruta_base = entrada_ruta.get().strip()
    rutas = []
    for i in indices:
        elemento = listbox.get(i).strip()
        if os.path.isabs(elemento):
            rutas.append(os.path.abspath(elemento))
        elif ruta_base == MOSTRAR_PC:
            rutas.append(elemento)
        else:
            rutas.append(os.path.abspath(os.path.join(ruta_base, elemento)))
    return rutas


def abrir_elemento_from_list(listbox, entrada_ruta, texto_salida):
    elementos = seleccionar_elementos(listbox, entrada_ruta)
    """Abre un solo elemento seleccionado desde el listbox."""
    if len(elementos) != 1:
        messagebox.showwarning("Selecciona uno", "Selecciona un solo elemento para abrir.")
        return
    abrir_elemento(elementos[0], entrada_ruta, texto_salida, listbox)


def renombrar_elemento_from_list(listbox, entrada_ruta, texto_salida):
    elementos = seleccionar_elementos(listbox, entrada_ruta)
    """Renombra un solo elemento seleccionado."""
    if len(elementos) != 1:
        messagebox.showwarning("Selecciona uno", "Selecciona un solo elemento para renombrar.")
        return
    renombrar_elemento(elementos[0], entrada_ruta, texto_salida)


def eliminar_elementos(listbox, entrada_ruta, texto_salida):
    elementos = seleccionar_elementos(listbox, entrada_ruta)
    """Elimina los elementos seleccionados, confirmando antes la acción."""
    if not elementos:
        return

    if len(elementos) == 1:
        pregunta = f"¿Eliminar '{os.path.basename(elementos[0])}'?"
    else:
        pregunta = f"¿Eliminar {len(elementos)} elementos seleccionados?"

    if not messagebox.askyesno("Confirmar eliminación", pregunta):
        return

    errores = []
    eliminados = 0
    for ruta in elementos:
        try:
            if os.path.isdir(ruta):
                shutil.rmtree(ruta)
            else:
                os.remove(ruta)
            eliminados += 1
        except Exception as e:
            errores.append(f"{os.path.basename(ruta)}: {str(e)}")

    if eliminados:
        messagebox.showinfo("Éxito", f"Eliminados {eliminados} elemento(s).")
    if errores:
        messagebox.showerror("Errores al eliminar", "\n".join(errores))

    carpeta_actual = entrada_ruta.get().strip()
    if os.path.exists(carpeta_actual):
        listar_archivos(carpeta_actual, texto_salida, listbox)


def copiar_elementos(listbox, entrada_ruta):
    global copy_buffer, clipboard_action
    elementos = seleccionar_elementos(listbox, entrada_ruta)
    """Copia los elementos seleccionados para pegarlos en otra ubicación."""
    if not elementos:
        return
    copy_buffer = elementos
    clipboard_action = "copy"
    messagebox.showinfo("Copiar", f"{len(elementos)} elemento(s) copiado(s).")


def cortar_elementos(listbox, entrada_ruta):
    global copy_buffer, clipboard_action
    elementos = seleccionar_elementos(listbox, entrada_ruta)
    """Corta los elementos seleccionados para moverlos a otra ubicación."""
    if not elementos:
        return
    copy_buffer = elementos
    clipboard_action = "cut"
    messagebox.showinfo("Cortar", f"{len(elementos)} elemento(s) listo(s) para mover.")


def pegar_elemento(entrada_ruta, texto_salida, listbox):
    global copy_buffer, clipboard_action
    """Pega los elementos copiados o cortados en la ruta actual."""
    if not copy_buffer or not clipboard_action:
        messagebox.showwarning("Portapapeles vacío", "Primero copia o corta elementos.")
        return

    destino = simpledialog.askstring("Pegar", "Ingresa la ruta de destino:", initialvalue=entrada_ruta.get().strip())
    if not destino:
        return

    if not os.path.isabs(destino):
        destino = os.path.abspath(os.path.join(entrada_ruta.get().strip(), destino))
    else:
        destino = os.path.abspath(destino)

    if not os.path.exists(destino):
        messagebox.showerror("Destino no existe", f"La ruta destino '{destino}' no existe.")
        return

    if not os.path.isdir(destino):
        messagebox.showerror("Destino inválido", "La ruta de destino debe ser una carpeta.")
        return

    errores = []
    exitos = 0
    for ruta in copy_buffer:
        destino_final = os.path.join(destino, os.path.basename(ruta))
        if os.path.exists(destino_final):
            errores.append(f"Ya existe: {os.path.basename(ruta)}")
            continue
        try:
            if clipboard_action == "copy":
                if os.path.isdir(ruta):
                    shutil.copytree(ruta, destino_final)
                else:
                    shutil.copy2(ruta, destino_final)
            else:
                shutil.move(ruta, destino_final)
            exitos += 1
        except Exception as e:
            errores.append(f"{os.path.basename(ruta)}: {str(e)}")

    if exitos:
        messagebox.showinfo("Pegar", f"{exitos} elemento(s) pegado(s) en {destino}.")
    if errores:
        messagebox.showerror("Errores al pegar", "\n".join(errores))

    if clipboard_action == "cut":
        copy_buffer = []
        clipboard_action = None

    if os.path.exists(destino):
        listar_archivos(destino, texto_salida, listbox)


def crear_carpeta(entrada_ruta, texto_salida, listbox):
    ruta_actual = entrada_ruta.get().strip()
    """Crea una nueva carpeta en la ruta actual."""
    if ruta_actual == MOSTRAR_PC:
        messagebox.showwarning("Ubicación inválida", "No puedes crear carpetas en This PC. Selecciona una unidad primero.")
        return
    
    if not ruta_actual or not os.path.exists(ruta_actual):
        messagebox.showerror("Ruta inválida", "Ingresa una ruta válida primero.")
        return
    
    nombre_carpeta = simpledialog.askstring("Crear Carpeta", "Ingresa el nombre de la nueva carpeta:")
    if not nombre_carpeta:
        return
    
    nombre_carpeta = nombre_carpeta.strip()
    if not nombre_carpeta:
        messagebox.showwarning("Nombre vacío", "El nombre de la carpeta no puede estar vacío.")
        return
    
    ruta_nueva = os.path.join(ruta_actual, nombre_carpeta)
    
    if os.path.exists(ruta_nueva):
        messagebox.showerror("Ya existe", f"La carpeta '{nombre_carpeta}' ya existe.")
        return
    
    try:
        os.makedirs(ruta_nueva, exist_ok=True)
        messagebox.showinfo("Éxito", f"Carpeta '{nombre_carpeta}' creada exitosamente.")
        listar_archivos(ruta_actual, texto_salida, listbox)
    except Exception as e:
        messagebox.showerror("Error al crear", f"No se pudo crear la carpeta: {str(e)}")


def abrir_elemento(ruta, entrada_ruta, texto_salida, listbox=None):
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
            cargar_ruta(ruta_completa, entrada_ruta, texto_salida, listbox)
        else:
            # Si es un archivo, abrirlo con la aplicación predeterminada
            os.startfile(ruta_completa)
            messagebox.showinfo("Éxito", f"Abriendo archivo: {ruta_completa}")
    except Exception as e:
        messagebox.showerror("Error al abrir", f"No se pudo abrir el elemento: {str(e)}")


def renombrar_elemento(ruta, entrada_ruta, texto_salida, listbox=None):
    """Renombra un archivo o carpeta dentro de la ruta base actual."""
    if not ruta:
        messagebox.showwarning("Ruta vacía", "Ingresa el elemento a renombrar.")
        return

    if not os.path.isabs(ruta):
        ruta_base = entrada_ruta.get().strip()
        ruta_completa = os.path.join(ruta_base, ruta) if ruta_base else ruta
    else:
        ruta_completa = ruta

    ruta_completa = os.path.abspath(ruta_completa)

    if not os.path.exists(ruta_completa):
        messagebox.showerror("Ruta no encontrada", f"La ruta '{ruta_completa}' no existe.")
        return

    nuevo_nombre = simpledialog.askstring("Renombrar", "Ingresa el nuevo nombre:", initialvalue=os.path.basename(ruta_completa))
    if not nuevo_nombre:
        return

    if nuevo_nombre == os.path.basename(ruta_completa):
        return

    nueva_ruta = os.path.join(os.path.dirname(ruta_completa), nuevo_nombre)
    if os.path.exists(nueva_ruta):
        messagebox.showerror("Nombre duplicado", f"Ya existe un elemento llamado '{nuevo_nombre}'.")
        return

    try:
        os.rename(ruta_completa, nueva_ruta)
        messagebox.showinfo("Éxito", f"Renombrado a: {nuevo_nombre}")
        carpeta_actual = os.path.dirname(ruta_completa)
        entrada_ruta.delete(0, tk.END)
        entrada_ruta.insert(0, carpeta_actual)
        listar_archivos(carpeta_actual, texto_salida, listbox)
    except Exception as e:
        messagebox.showerror("Error al renombrar", f"No se pudo renombrar: {str(e)}")


def eliminar_elemento(ruta, entrada_ruta, texto_salida, listbox=None):
    """Elimina un archivo o carpeta, confirmando antes la acción."""
    if not ruta:
        messagebox.showwarning("Ruta vacía", "Ingresa el elemento a eliminar.")
        return

    if not os.path.isabs(ruta):
        ruta_base = entrada_ruta.get().strip()
        ruta_completa = os.path.join(ruta_base, ruta) if ruta_base else ruta
    else:
        ruta_completa = ruta

    ruta_completa = os.path.abspath(ruta_completa)

    if not os.path.exists(ruta_completa):
        messagebox.showerror("Ruta no encontrada", f"La ruta '{ruta_completa}' no existe.")
        return

    nombre_elemento = os.path.basename(ruta_completa)
    if not messagebox.askyesno("Confirmar eliminación", f"¿Eliminar '{nombre_elemento}'?"):
        return

    try:
        if os.path.isdir(ruta_completa):
            shutil.rmtree(ruta_completa)
        else:
            os.remove(ruta_completa)

        messagebox.showinfo("Éxito", f"Elemento eliminado: {nombre_elemento}")
        carpeta_actual = os.path.dirname(ruta_completa)
        entrada_ruta.delete(0, tk.END)
        entrada_ruta.insert(0, carpeta_actual)
        listar_archivos(carpeta_actual, texto_salida, listbox)
    except Exception as e:
        messagebox.showerror("Error al eliminar", f"No se pudo eliminar: {str(e)}")


if __name__ == "__main__":
    """Función principal que inicia la interfaz gráfica"""
    ventana = tk.Tk()
    ventana.title("Organizador de Archivos")

    #Cargar el icono de la aplicación si está disponible
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(app_dir, "icons8-cricket-64.png")
        if os.path.exists(icon_path):
            _icon_img = tk.PhotoImage(file=icon_path)
            ventana.iconphoto(True, _icon_img)
    except Exception:
        # No bloquear la aplicación si el icono falla
        pass

    ventana.geometry("860x950")
    ventana.resizable(False, False)
    ventana.configure(bg="#2b2b2b")

    etiqueta_ruta = tk.Label(ventana, text="Ruta de acceso:", font=("Segoe UI", 11), bg="#2b2b2b", fg="white")
    etiqueta_ruta.pack(pady=(20, 4), padx=20, anchor="w")

    entrada_ruta = tk.Entry(ventana, width=80, font=("Segoe UI", 10), bg="#333333", fg="white", insertbackground="white")
    entrada_ruta.pack(padx=20)

    etiqueta_busqueda = tk.Label(ventana, text="Buscar por nombre:", font=("Segoe UI", 11), bg="#2b2b2b", fg="white")
    etiqueta_busqueda.pack(pady=(16, 4), padx=20, anchor="w")

    entrada_busqueda = tk.Entry(ventana, width=80, font=("Segoe UI", 10), bg="#333333", fg="white", insertbackground="white")
    entrada_busqueda.pack(padx=20)

    boton_frame = tk.Frame(ventana, bg="#2b2b2b")
    boton_frame.pack(pady=14)

    boton_listar = tk.Button(
        #Botón para listar el contenido de la carpeta actual
        boton_frame,
        text="Listar carpeta",
        font=("Segoe UI", 10, "bold"),
        command=lambda: cargar_ruta(entrada_ruta.get().strip(), entrada_ruta, texto_salida, listbox),
        bg="#4CAF50",
        fg="white",
        activebackground="#45A049",
        padx=14,
        pady=8,
    )
    boton_listar.grid(row=0, column=0, padx=6)

    boton_this_pc = tk.Button(
        #Botón para mostrar las unidades de disco disponibles
        boton_frame,
        text="This PC",
        font=("Segoe UI", 10, "bold"),
        command=lambda: mostrar_this_pc(texto_salida, listbox, entrada_ruta),
        bg="#8E44AD",
        fg="white",
        activebackground="#6C3483",
        padx=14,
        pady=8,
    )
    boton_this_pc.grid(row=0, column=3, padx=6)

    boton_buscar = tk.Button(
        #Botón para buscar
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

    boton_atras = tk.Button(
        #Botón para regresar a la ruta anterior
        boton_frame,
        text="Atrás",
        font=("Segoe UI", 10, "bold"),
        command=lambda: regresar_ruta_anterior(entrada_ruta, texto_salida, listbox),
        bg="#9E9E9E",
        fg="white",
        activebackground="#757575",
        padx=14,
        pady=8,
    )
    boton_atras.grid(row=0, column=2, padx=6)

    #Barra de progreso para mostrar el avance de la búsqueda
    barra_progreso = ttk.Progressbar(ventana, mode='determinate', length=600)
    barra_progreso.pack(padx=20, pady=(10, 8), fill=tk.X)

    #Etiqueta para mostrar el contenido de la carpeta
    etiqueta_contenido = tk.Label(ventana, text="Contenido de la carpeta:", font=("Segoe UI", 11), bg="#2b2b2b", fg="white")
    etiqueta_contenido.pack(pady=(10, 4), padx=20, anchor="w")

    #listbox para mostrar los archivos y carpetas encontrados
    listbox_frame = tk.Frame(ventana, bg="#2b2b2b")
    listbox_frame.pack(padx=20, fill=tk.BOTH, expand=False)

    listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED, width=80, height=12, font=("Segoe UI", 10), bg="#1e1e1e", fg="white", selectbackground="#555555", selectforeground="white")
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    #Scrollbar para el listbox
    scrollbar_list = tk.Scrollbar(listbox_frame, command=listbox.yview)
    scrollbar_list.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scrollbar_list.set)

    #Etiqueta de información sobre la selección múltiple
    info_label = tk.Label(ventana, text="Usa Ctrl o Shift para seleccionar varios elementos.", font=("Segoe UI", 9), fg="#ddd", bg="#2b2b2b")
    info_label.pack(padx=20, anchor="w")

    #Frame para los botones de acciones (abrir, renombrar, eliminar, copiar, cortar, pegar, nueva carpeta)
    acciones_frame = tk.Frame(ventana, bg="#2b2b2b")
    acciones_frame.pack(pady=10)

    """Botones de acciones"""
    boton_abrir = tk.Button(
        acciones_frame,
        text="Abrir",
        font=("Segoe UI", 10),
        command=lambda: abrir_elemento_from_list(listbox, entrada_ruta, texto_salida),
        bg="#000000",
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
        command=lambda: renombrar_elemento_from_list(listbox, entrada_ruta, texto_salida),
        bg="#81381E",
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
        command=lambda: eliminar_elementos(listbox, entrada_ruta, texto_salida),
        bg="#E40303",
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
        command=lambda: copiar_elementos(listbox, entrada_ruta),
        bg="#0076EC",
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
        command=lambda: cortar_elementos(listbox, entrada_ruta),
        bg="#F3B007",
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
        command=lambda: pegar_elemento(entrada_ruta, texto_salida, listbox),
        bg="#0BE015",
        fg="white",
        activebackground="#2E7D32",
        padx=12,
        pady=6,
    )
    boton_pegar.grid(row=1, column=2, padx=4, pady=4)

    boton_crear = tk.Button(
        acciones_frame,
        text="Nueva Carpeta",
        font=("Segoe UI", 10),
        command=lambda: crear_carpeta(entrada_ruta, texto_salida, listbox),
        bg="#00BCD4",
        fg="white",
        activebackground="#0097A7",
        padx=12,
        pady=6,
    )
    boton_crear.grid(row=2, column=0, padx=4, pady=4)

    #Permite abrir un elemento con doble clic en el listbox
    listbox.bind('<Double-Button-1>', lambda event: abrir_elemento_from_list(listbox, entrada_ruta, texto_salida))
    
    #Etiqueta para mostrar los resultados de la búsqueda o mensajes de estado
    texto_salida = tk.Text(ventana, width=78, height=24, font=("Consolas", 10), bg="#121212", fg="#e0e0e0", insertbackground="white", state="disabled", wrap="word")
    texto_salida.pack(padx=20, pady=(0, 10))

    #Scrollbar para el texto de salida
    scrollbar = tk.Scrollbar(ventana, command=texto_salida.yview)
    texto_salida.config(yscrollcommand=scrollbar.set)
    scrollbar.place(relx=0.975, rely=0.28, relheight=0.56)

    #Cargar la ruta inicial al iniciar la aplicación
    mostrar_this_pc(texto_salida, listbox, entrada_ruta, agregar_al_historial=False)

    ventana.mainloop()

