import cv2
import numpy as np
import os
import random
import yaml  # Importar el módulo yaml


def cargar_imagenes(directorio):
    """Carga imágenes PNG desde un directorio, ordenadas, y devuelve una lista de tuplas (imagen, clase_id)."""
    imagenes = []
    archivos = sorted([f for f in os.listdir(directorio) if f.lower().endswith('.png')])
    for i, archivo in enumerate(archivos):
        ruta = os.path.join(directorio, archivo)
        img = cv2.imread(ruta, cv2.IMREAD_UNCHANGED)
        if img is not None:
            imagenes.append((img, i))  # Almacenar la imagen y su ID de clase (índice)
    return imagenes


def rotar_imagen(imagen, angulo):
    """Rota una imagen un ángulo dado y ajusta el tamaño para que no se recorte."""
    (h, w) = imagen.shape[:2]
    centro = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(centro, angulo, 1.0)

    # Calcular las nuevas dimensiones de la imagen rotada
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    nuevo_w = int((w * cos) + (h * sin))
    nuevo_h = int((w * sin) + (h * cos))

    # Ajustar la matriz de transformación para el nuevo centro
    M[0, 2] += (nuevo_w - w) // 2
    M[1, 2] += (nuevo_h - h) // 2

    return cv2.warpAffine(
        imagen,
        M,
        (nuevo_w, nuevo_h),
        flags=cv2.INTER_AREA,  # Mejor interpolación para reducir
        borderMode=cv2.BORDER_CONSTANT,  # Rellenar con transparente
        borderValue=(0, 0, 0, 0),
    )


def ajustar_transparencia(img):
    """Recorta las áreas transparentes de una imagen PNG."""
    if img.shape[2] == 4:  # Si tiene canal alfa
        alpha = img[:, :, 3]
        coords = cv2.findNonZero(alpha)  # Encuentra los píxeles no transparentes
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)  # Obtiene el rectángulo delimitador
            return img[y : y + h, x : x + w]
    return img  # Si no tiene canal alfa, devuelve la imagen original


def sobreponen(rect1, rect2):
    """Comprueba si dos rectángulos se superponen."""
    x1, y1, w1, h1 = rect1
    x2, y2, w2, h2 = rect2

    # Si un rectángulo está a la izquierda del otro
    if (x1 >= (x2 + w2)) or ((x1 + w1) <= x2):
        return False
    # Si un rectángulo está arriba del otro
    if (y1 >= (y2 + h2)) or ((y1 + h1) <= y2):
        return False
    return True  # Se superponen


def generar_imagen(imagenes, num_imagenes, output_img, output_txt):
    """Genera una imagen compuesta y su archivo de anotaciones YOLO."""
    fondo = np.ones((640, 640, 3), dtype=np.uint8) * 255
    cajas = []

    with open(output_txt, "w") as archivo:
        for _ in range(num_imagenes):
            if not imagenes:
                break

            # Seleccionar imagen y su clase
            img, clase_id = random.choice(imagenes)

            # Escalar
            escala = random.uniform(0.1, 0.5)
            img_escalada = cv2.resize(
                img, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA
            )

            # Rotar
            angulo = random.uniform(0, 360)
            img_rotada = rotar_imagen(img_escalada, angulo)

            # Recortar áreas transparentes
            img_final = ajustar_transparencia(img_rotada)
            if img_final is None or img_final.size == 0:
                continue

            h, w = img_final.shape[:2]
            if w == 0 or h == 0 or w > 640 or h > 640:  # Evitar imagenes muy grandes
                continue

            # Intentar colocar la imagen
            colocada = False
            intentos = 100

            for _ in range(intentos):
                x = random.randint(0, 640 - w)
                y = random.randint(0, 640 - h)
                nueva_caja = (x, y, w, h)

                # Verificar colisiones
                colision = False
                for c in cajas:
                    if sobreponen(nueva_caja, c):
                        colision = True
                        break

                if not colision:
                    # Superponer la imagen (con transparencia)
                    if img_final.shape[2] == 4:  # Si tiene canal alfa
                        alpha = img_final[:, :, 3] / 255.0  # Normalizar alfa
                        overlay = img_final[:, :, :3]  # Solo los canales RGB

                        roi = fondo[y : y + h, x : x + w]  # Region of Interest
                        for c in range(3):  # Mezclar cada canal de color
                            roi[:, :, c] = (1 - alpha) * roi[:, :, c] + alpha * overlay[:, :, c]
                    else:  # Si no tiene canal alfa, simplemente copiar
                        fondo[y : y + h, x : x + w] = img_final[:, :, :3]

                    # Escribir bounding box en formato YOLO
                    x_centro = (x + w / 2) / 640.0
                    y_centro = (y + h / 2) / 640.0
                    ancho = w / 640.0
                    alto = h / 640.0

                    archivo.write(
                        f"{clase_id} {x_centro:.6f} {y_centro:.6f} {ancho:.6f} {alto:.6f}\n"
                    )
                    cajas.append(nueva_caja)
                    colocada = True
                    break

            if not colocada:
                # print(f"No se pudo colocar la imagen después de {intentos} intentos.")
                continue  # Si no se pudo colocar, pasar a la siguiente imagen

    cv2.imwrite(output_img, fondo)


def generar_dataset(imagenes_disponibles, tamano_dataset, num_imagenes_por_muestra):
    """Genera el dataset completo de imágenes y anotaciones."""

    # Crear directorios si no existen
    dataset_dir = "dataset"
    images_dir = os.path.join(dataset_dir, "images")
    labels_dir = os.path.join(dataset_dir, "labels")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)
     # Generar nombres de clases a partir de los nombres de archivo
    nombres_clases = [os.path.splitext(f)[0] for f in os.listdir("img") if f.lower().endswith('.png')]


    # Generar archivo data.yaml
    data_yaml = {
        "train": "../images",  # Rutas relativas desde la ubicación de data.yaml
        "val": "../images",  # Usaremos el mismo conjunto para train y val en este ejemplo
        "nc": len(imagenes_disponibles),
        "names": nombres_clases, # Usar los nombres de archivo como nombres de clase
    }
    with open(os.path.join(dataset_dir, "data.yaml"), "w") as f:
        yaml.dump(data_yaml, f, default_flow_style=False)


    for i in range(tamano_dataset):
        nombre_base = f"imagen_{i:04d}"  # Formato de nombre de archivo
        ruta_imagen = os.path.join(images_dir, f"{nombre_base}.png")
        ruta_etiqueta = os.path.join(labels_dir, f"{nombre_base}.txt")
        generar_imagen(imagenes_disponibles, num_imagenes_por_muestra, ruta_imagen, ruta_etiqueta)
        print(f"Generada: {ruta_imagen} y {ruta_etiqueta}")



if __name__ == "__main__":
    imagenes = cargar_imagenes("img")
    if not imagenes:
        print("No se encontraron imágenes PNG en el directorio 'img'")
        exit()

    tamano_dataset = int(input("Ingrese el tamaño del dataset a generar: "))
    num_imagenes_por_muestra = int(
        input("Ingrese el número de imágenes a incluir en cada muestra: ")
    )

    generar_dataset(imagenes, tamano_dataset, num_imagenes_por_muestra)
    print("Dataset generado en la carpeta 'dataset'")