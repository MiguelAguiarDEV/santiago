import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import os
import platform

class VideoProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Seleccionador de Fotogramas de Video")
        #self.root.state("zoomed")

        # Variables de control
        self.video_path = None
        self.frame_interval = 10
        self.original_frames = {}
        self.thumbnail_items = []
        self.selected_frames = set()
        self.thumbnail_width = 256  # Ancho fijo para miniaturas
        self.margin = 10

        self.os_platform = platform.system()
        self.create_widgets()
        self.resize_after_id = None

    def create_widgets(self):
        # Frame superior: botones, entrada y barra de progreso
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.load_button = tk.Button(top_frame, text="Cargar Video", command=self.load_video)
        self.load_button.pack(side=tk.LEFT, padx=5)

        tk.Label(top_frame, text="N (1 de cada N fotogramas):").pack(side=tk.LEFT, padx=5)
        self.entry_n = tk.Entry(top_frame, width=5)
        self.entry_n.insert(0, "10")
        self.entry_n.pack(side=tk.LEFT, padx=5)

        self.process_button = tk.Button(top_frame, text="Procesar Video", command=self.process_video, state=tk.DISABLED)
        self.process_button.pack(side=tk.LEFT, padx=5)

        self.save_button = tk.Button(top_frame, text="Guardar Seleccionados", command=self.save_selected, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(top_frame, orient="horizontal", mode="determinate", length=200)
        self.progress.pack(side=tk.LEFT, padx=5)

        # Área central: Canvas para miniaturas con scrollbar
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="white")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Configurar eventos
        self.canvas.bind("<Enter>", lambda event: self.canvas.focus_set())
        if self.os_platform == "Windows":
            self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        elif self.os_platform == "Darwin":
            self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        else:
            self.canvas.bind("<Button-4>", self.on_mousewheel)
            self.canvas.bind("<Button-5>", self.on_mousewheel)

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.root.bind("<Configure>", self.on_resize)

    def create_proportional_thumbnail(self, frame):
        # Convertir de BGR a RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        
        # Calcular altura proporcional manteniendo el ancho en 256
        width_percent = self.thumbnail_width / float(pil_image.size[0])
        proportional_height = int(float(pil_image.size[1]) * float(width_percent))
        
        # Redimensionar manteniendo la proporción
        thumb = pil_image.resize((self.thumbnail_width, proportional_height), Image.Resampling.LANCZOS)
        return thumb, proportional_height

    def process_video(self):
        try:
            n_value = int(self.entry_n.get())
            if n_value <= 0:
                raise ValueError("El valor de N debe ser mayor a 0.")
            self.frame_interval = n_value

            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise ValueError("No se pudo abrir el video.")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.progress["maximum"] = total_frames

            current_frame = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                self.progress["value"] = current_frame
                self.root.update_idletasks()

                if current_frame % self.frame_interval == 0:
                    self.original_frames[current_frame] = frame.copy()
                    
                    # Crear miniatura proporcional
                    thumb, thumb_height = self.create_proportional_thumbnail(frame)
                    photo = ImageTk.PhotoImage(thumb)

                    # Crear rectángulo y imagen
                    rect_id = self.canvas.create_rectangle(0, 0, self.thumbnail_width, thumb_height,
                                                       outline="black", width=5)
                    img_id = self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                    
                    self.canvas.itemconfig(rect_id, tags=("thumbnail",))
                    self.canvas.itemconfig(img_id, tags=("thumbnail",))
                    
                    self.thumbnail_items.append({
                        "frame_number": current_frame,
                        "photo_image": photo,
                        "img_id": img_id,
                        "rect_id": rect_id,
                        "x": 0,
                        "y": 0,
                        "height": thumb_height  # Guardar la altura para el reposicionamiento
                    })
                current_frame += 1

            cap.release()
            self.progress["value"] = total_frames
            self.save_button.config(state=tk.NORMAL)
            self.reposition_thumbnails()
        except Exception as e:
            messagebox.showerror("Error", f"Error al procesar video: {e}")

    def reposition_thumbnails(self):
        try:
            canvas_width = self.canvas.winfo_width()
            if canvas_width <= 0:
                canvas_width = self.canvas.winfo_reqwidth()
            
            cols = max(1, canvas_width // (self.thumbnail_width + self.margin))
            current_row_y = self.margin
            current_col = 0
            max_height_in_row = 0
            
            for item in self.thumbnail_items:
                if current_col >= cols:
                    current_col = 0
                    current_row_y += max_height_in_row + self.margin
                    max_height_in_row = 0
                
                x = current_col * (self.thumbnail_width + self.margin) + self.margin
                y = current_row_y
                
                item["x"] = x
                item["y"] = y
                self.canvas.coords(item["rect_id"], x, y, 
                                 x + self.thumbnail_width, 
                                 y + item["height"])
                self.canvas.coords(item["img_id"], x, y)
                
                max_height_in_row = max(max_height_in_row, item["height"])
                current_col += 1
            
            # Actualizar el área de scroll
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
        except Exception as e:
            print(f"Error en reposition_thumbnails: {e}")

    def save_selected(self):
        try:
            if not self.selected_frames:
                messagebox.showinfo("Información", "No hay fotogramas seleccionados para guardar.")
                return

            # Configurar barra de progreso para el guardado
            total_frames = len(self.selected_frames)
            self.progress["maximum"] = total_frames
            self.progress["value"] = 0
            
            if not os.path.exists("imagenes"):
                os.makedirs("imagenes")
            
            frames_guardados = 0
            for i, frame_num in enumerate(self.selected_frames):
                if frame_num in self.original_frames:
                    frame = self.original_frames[frame_num]
                    filename = os.path.join("imagenes", f"frame_{frame_num:04d}.png")
                    cv2.imwrite(filename, frame)
                    frames_guardados += 1
                    
                    # Actualizar barra de progreso
                    self.progress["value"] = i + 1
                    self.root.update_idletasks()
            
            messagebox.showinfo("Éxito", 
                              f"Se han guardado {frames_guardados} fotogramas correctamente en la carpeta 'imagenes'.")
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar fotogramas: {e}")

    def load_video(self):
        try:
            video_file = filedialog.askopenfilename(
                filetypes=[("Archivos de Video", "*.mp4;*.avi;*.mov;*.mkv")])
            if not video_file:
                return
            self.video_path = video_file

            self.original_frames.clear()
            self.thumbnail_items.clear()
            self.selected_frames.clear()
            self.canvas.delete("all")
            self.progress["value"] = 0
            self.process_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar video: {e}")

    def on_canvas_click(self, event):
        try:
            item = self.canvas.find_closest(event.x, event.y)
            if not item:
                return
            tags = self.canvas.gettags(item)
            if "thumbnail" not in tags:
                return
            
            clicked_item = None
            for thumb in self.thumbnail_items:
                if item[0] in (thumb["img_id"], thumb["rect_id"]):
                    clicked_item = thumb
                    break
            if clicked_item is None:
                return
            
            frame_num = clicked_item["frame_number"]
            if frame_num in self.selected_frames:
                self.selected_frames.remove(frame_num)
                self.canvas.itemconfig(clicked_item["rect_id"], outline="black")
            else:
                self.selected_frames.add(frame_num)
                self.canvas.itemconfig(clicked_item["rect_id"], outline="red")
        except Exception as e:
            messagebox.showerror("Error", f"Error al seleccionar miniatura: {e}")

    def on_mousewheel(self, event):
        try:
            if self.os_platform == "Windows":
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif self.os_platform == "Darwin":
                self.canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                if event.num == 4:
                    self.canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.canvas.yview_scroll(1, "units")
        except Exception as e:
            print(f"Error en on_mousewheel: {e}")

    def on_resize(self, event):
        if self.resize_after_id:
            self.root.after_cancel(self.resize_after_id)
        self.resize_after_id = self.root.after(300, self.reposition_thumbnails)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoProcessorApp(root)
    root.mainloop()