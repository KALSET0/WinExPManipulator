# ThreadDrive Explorer 

Un explorador de archivos y gestor de sistema ligero para Windows desarrollado en Python. Este proyecto va más allá de un script básico, implementando una arquitectura concurrente con interfaz gráfica para ofrecer operaciones fluidas en el sistema de archivos sin congelar la experiencia del usuario.

##  Características Clave
- **Navegación Nativa:** Conexión directa al núcleo de Windows mediante llamadas de sistema para listar unidades físicas (`This PC`).
- **Operaciones CRUD de Archivos:** Capacidad completa para copiar, cortar, pegar, borrar, renombrar y crear carpetas con confirmaciones de seguridad.
- **Selección Múltiple:** Soporte nativo para operar con múltiples archivos simultáneamente utilizando `Ctrl` o `Shift`.
- **Búsqueda Avanzada Indexada:** Motor de búsqueda capaz de escanear desde rutas locales hasta la raíz del disco (`C:\`).

##  Desafíos Técnicos Superados (Backend Focus)

### 1. Concurrencia y Multihilo (`threading` + `Queue`)
El mayor desafío de un File Explorer es evitar que la interfaz gráfica se congele ("No Responde") al realizar operaciones pesadas como recorrer discos enteros. 
- **Solución:** Se delegó el motor de búsqueda a un hilo secundario independiente (`threading.Thread`). 
- **Comunicación Segura:** La sincronización y actualización de la barra de progreso en tiempo real se maneja mediante colas de datos (`queue.Queue`), garantizando un flujo de información seguro entre hilos sin corromper la memoria de la GUI.

### 2. Filtros de Búsqueda con Expresiones Regulares Avanzadas (`re`)
Para evitar resultados ruidosos o colapsos por cadenas de texto masivas, el motor implementa expresiones regulares con *Lookbehinds* y *Lookaheads* negativos:
- Permite prefijos y sufijos inteligentes para tolerar ligeras variaciones en los nombres, pero descarta coincidencias caóticas en el sistema.

### 3. Interacción de Bajo Nivel con Windows (`ctypes`)
En lugar de hardcodear rutas estáticas, el sistema consulta dinámicamente la API de Windows (`kernel32.GetLogicalDrives`) usando una máscara de bits para identificar exactamente qué discos de almacenamiento están montados en el hardware en tiempo real.

##  Tecnologías y Librerías Utilizadas
- **Python 3.x** (Lenguaje principal)
- **Tkinter / ttk** (Interfaz Gráfica de Usuario)
- **OS & Shutil** (Manipulación del Sistema de Archivos nativo)
- **Threading & Queue** (Gestión de concurrencia y subprocesos)
- **Re** (Procesamiento de texto y expresiones regulares)

## 📦 Instalación y Ejecución

1. Clona este repositorio en tu máquina local:
    Bash

    git clone [https://github.com/KALSET0/PyNav-OS.git](https://github.com/KALSET0/PyNav-OS.git)