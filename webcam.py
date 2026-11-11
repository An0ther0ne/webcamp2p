import tkinter as tk
import cv2
from PIL import Image, ImageTk

# Ініціалізація вікна Tkinter
root = tk.Tk()
root.title("Webcam Realtime")
root.geometry("640x420")

# Відкриваємо веб-камеру через DirectShow
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("Помилка: Не вдалося отримати доступ до веб-камери.")
    exit()

# 1. СПОЧАТКУ пакуємо кнопку зверху, щоб вона гарантовано була видима
def open_camera_settings():
    try:
        cap.set(cv2.CAP_PROP_SETTINGS, 1)
    except Exception as e:
        print(f"Не вдалося відкрити налаштування: {e}")

btn_settings = tk.Button(root, text="⚙️ Налаштування камери ( Anti-Flicker 50Hz )", command=open_camera_settings, bg="#ddd", font=("Arial", 10), height=2)
btn_settings.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

# 2. ПОТІМ пакуємо область відео, яка займатиме весь решток вікна
lmain = tk.Label(root)
lmain.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

def update_frame():
    ret, frame = cap.read()
    
    if ret and frame is not None:
        width = lmain.winfo_width()
        height = lmain.winfo_height()
        
        # Масштабуємо кадр під поточний розмір вікна
        if width > 10 and height > 10:
            frame = cv2.resize(frame, (width, height))
        
        # Конвертуємо кольори з OpenCV (BGR) у формат для Tkinter (RGB)
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        
        lmain.imgtk = imgtk
        lmain.configure(image=imgtk)
    
    root.after(30, update_frame)

def close_app(event=None):
    try:
        cap.release()
    except:
        pass
    root.destroy()

# Закриття хрестиком
root.protocol("WM_DELETE_WINDOW", close_app)

# Універсальний обробник клавіш (ESC або 'q' / 'Q')
def handle_keypress(event):
    if event.keysym in ('Escape', 'q', 'Q'):
        close_app()

root.bind('<Key>', handle_keypress)

# Запуск циклу оновлення
update_frame()

# Головний цикл додатку
root.mainloop()
