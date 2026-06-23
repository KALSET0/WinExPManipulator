import os

ruta_test = input("Ingrese la ruta de la carpeta que desea leer: ")
print('')

def listar_archivos(ruta_carpeta):
    """
    Función que lee y muestra los archivos dentro de una ruta específica.
    """
    # Verificamos si la ruta ingresada realmente existe
    if os.path.exists(ruta_carpeta):
        print(f"✅ Conexión exitosa. Leyendo la ruta...: {ruta_carpeta}\n")
        
        # os.listdir nos devuelve una lista con los nombres de los archivos y carpetas
        elementos = os.listdir(ruta_carpeta)
        
        if not elementos:
            print("⚠️ La carpeta está vacía.")
            return

        print("--- Archivos encontrados ---")
        for elemento in elementos:
            print(f"- {elemento}")
            
    else:
        print(f"❌ Error: La ruta '{ruta_carpeta}' no existe. Verifica que esté bien escrita.")

    
listar_archivos(ruta_test)