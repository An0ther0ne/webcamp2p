# -*- coding: utf-8 -*-
import socket
import struct
import threading
import time
import tkinter as tk
import cv2
import numpy as np
from PIL import Image, ImageTk


class P2PWebcamApp:

  def __init__(self, root):
    self.root = root
    self.root.title("P2P Dual Stream")
    self.root.geometry("1900x540")

    # Ініціалізація веб-камери
    self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    self.has_camera = self.cap.isOpened()
    W, H = 640, 360
    self.black_frame = np.zeros((H, W, 3), dtype=np.uint8)

    self.conn_send = None
    self.conn_recv = None
    self.is_connected = False

    self.current_local_frame = self.black_frame
    self.current_remote_frame = self.black_frame

    # --- ПАНЕЛЬ КЕРУВАННЯ ---
    ctrl_frame = tk.Frame(root, bg="#e0e0e0", padx=5, pady=5)
    ctrl_frame.pack(side=tk.TOP, fill=tk.X)

    def open_settings():
      if self.has_camera:
        try:
          self.cap.set(cv2.CAP_PROP_SETTINGS, 1)
        except Exception:
          pass

    self.btn_set = tk.Button(
        ctrl_frame,
        text="⚙️ Камера",
        command=open_settings,
        bg="#ddd",
        font=("Arial", 9, "bold"),
    )
    if not self.has_camera:
      self.btn_set.config(state=tk.DISABLED)
    self.btn_set.pack(side=tk.LEFT, padx=3)

    tk.Label(ctrl_frame, text="IP:", bg="#e0e0e0", font=("Arial", 9)).pack(
        side=tk.LEFT, padx=2
    )
    self.ip_entry = tk.Entry(ctrl_frame, width=12, font=("Arial", 9))
    self.ip_entry.pack(side=tk.LEFT, padx=2)
    self.ip_entry.insert(0, "127.0.0.1")

    tk.Label(
        ctrl_frame, text="Мій порт:", bg="#e0e0e0", font=("Arial", 9)
    ).pack(side=tk.LEFT, padx=2)
    self.my_port_entry = tk.Entry(ctrl_frame, width=6, font=("Arial", 9))
    self.my_port_entry.pack(side=tk.LEFT, padx=2)
    self.my_port_entry.insert(0, "5000")

    tk.Label(
        ctrl_frame, text="Порт відпр.:", bg="#e0e0e0", font=("Arial", 9)
    ).pack(side=tk.LEFT, padx=2)
    self.send_port_entry = tk.Entry(ctrl_frame, width=6, font=("Arial", 9))
    self.send_port_entry.pack(side=tk.LEFT, padx=2)
    self.send_port_entry.insert(0, "5001")

    def swap_ports():
      p1 = self.my_port_entry.get()
      p2 = self.send_port_entry.get()
      self.my_port_entry.delete(0, tk.END)
      self.my_port_entry.insert(0, p2)
      self.send_port_entry.delete(0, tk.END)
      self.send_port_entry.insert(0, p1)

    self.btn_swap = tk.Button(
        ctrl_frame,
        text="🔄 Дзеркало портів",
        command=swap_ports,
        bg="#fff3cd",
        font=("Arial", 9),
    )
    self.btn_swap.pack(side=tk.LEFT, padx=5)

    self.btn_listen = tk.Button(
        ctrl_frame,
        text="Сервер",
        command=self.start_server,
        bg="#cce5ff",
        font=("Arial", 9, "bold"),
    )
    self.btn_listen.pack(side=tk.LEFT, padx=4)

    self.btn_connect = tk.Button(
        ctrl_frame,
        text="Клієнт",
        command=self.start_client,
        bg="#d4edda",
        font=("Arial", 9, "bold"),
    )
    self.btn_connect.pack(side=tk.LEFT, padx=4)

    self.status_lbl = tk.Label(
        ctrl_frame,
        text="Статус: Не підключено",
        fg="red",
        bg="#e0e0e0",
        font=("Arial", 9, "bold"),
    )
    self.status_lbl.pack(side=tk.RIGHT, padx=5)

    # --- ЗАЛІЗОБЕТОННИЙ РОЗДІЛ НА ДВА ВІКНА ЧЕРЕЗ GRID ---
    video_frame = tk.Frame(root, bg="#f0f0f0")
    video_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Налаштування сітки: рівно дві колонки по 50% ширини
    video_frame.columnconfigure(0, weight=1, uniform="group1")
    video_frame.columnconfigure(1, weight=1, uniform="group1")
    video_frame.rowconfigure(0, weight=1)

    # 1. ЛІВЕ ВІКНО (Колонка 0)
    local_box = tk.LabelFrame(
        video_frame,
        text=(
            " 1. Моя камера (Local) "
            if self.has_camera
            else " 1. Моя камера [Чорний екран] "
        ),
        font=("Arial", 10, "bold"),
    )
    local_box.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)
    self.lbl_local = tk.Label(local_box, bg="black")
    self.lbl_local.pack(fill=tk.BOTH, expand=True)

    # 2. ПРАВЕ ВІКНО (Колонка 1) — тепер воно фізично не зможе сховатися чи зникнути
    remote_box = tk.LabelFrame(
        video_frame,
        text=" 2. Віддалений потік (Remote) ",
        font=("Arial", 10, "bold"),
    )
    remote_box.grid(row=0, column=1, sticky="nsew", padx=3, pady=3)
    self.lbl_remote = tk.Label(
        remote_box,
        text="Очікування підключення...",
        fg="gray",
        bg="black",
        font=("Arial", 11),
    )
    self.lbl_remote.pack(fill=tk.BOTH, expand=True)

    self.local_imgtk = None
    self.remote_imgtk = None

    threading.Thread(target=self._capture_loop, daemon=True).start()
    self.update_gui()

    self.root.protocol("WM_DELETE_WINDOW", self.on_close)

  def _capture_loop(self):
    while True:
      if self.has_camera:
        ret, frame = self.cap.read()
        if ret and frame is not None:
          self.current_local_frame = frame
        else:
          self.current_local_frame = self.black_frame
      else:
        self.current_local_frame = self.black_frame
      time.sleep(0.03)

  def update_gui(self):
    # Рендер лівого вікна
    w_l = self.lbl_local.winfo_width()
    h_l = self.lbl_local.winfo_height()
    if w_l > 10 and h_l > 10:
      frame_l = cv2.resize(self.current_local_frame, (w_l, h_l))
      img_l = Image.fromarray(cv2.cvtColor(frame_l, cv2.COLOR_BGR2RGB))
      self.local_imgtk = ImageTk.PhotoImage(image=img_l)
      self.lbl_local.configure(image=self.local_imgtk, text="")

    # Рендер правого вікна
    w_r = self.lbl_remote.winfo_width()
    h_r = self.lbl_remote.winfo_height()
    if self.is_connected and w_r > 10 and h_r > 10:
      frame_r = cv2.resize(self.current_remote_frame, (w_r, h_r))
      img_r = Image.fromarray(cv2.cvtColor(frame_r, cv2.COLOR_BGR2RGB))
      self.remote_imgtk = ImageTk.PhotoImage(image=img_r)
      self.lbl_remote.configure(image=self.remote_imgtk, text="")
    elif not self.is_connected and w_r > 10 and h_r > 10:
      self.lbl_remote.configure(image="", text="Очікування підключення...", fg="gray")

    self.root.after(30, self.update_gui)

  def start_server(self):
    self.lock_ui()
    threading.Thread(target=self._server_thread, daemon=True).start()

  def _server_thread(self):
    try:
      my_port = int(self.my_port_entry.get())
      send_port = int(self.send_port_entry.get())

      server_recv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      server_recv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      server_recv.bind(("0.0.0.0", my_port))
      server_recv.listen(1)

      self.status_lbl.config(
          text=f"Статус: Очікування на порті {my_port}...", fg="blue"
      )
      conn_r, addr = server_recv.accept()
      self.conn_recv = conn_r
      server_recv.close()

      target_ip = addr[0]
      self.status_lbl.config(
          text=f"Статус: З'єднано з {target_ip}. Підключаюсь відправку...",
          fg="blue",
      )

      time.sleep(0.5)

      conn_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      conn_s.connect((target_ip, send_port))
      self.conn_send = conn_s

      self.is_connected = True
      self.status_lbl.config(
          text=f"Статус: Повністю підключено з {target_ip}", fg="green"
      )
      self._start_io_loops()
    except Exception as e:
      self.status_lbl.config(text=f"Помилка: {e}", fg="red")
      self.handle_disconnect()

  def start_client(self):
    self.lock_ui()
    threading.Thread(target=self._client_thread, daemon=True).start()

  def _client_thread(self):
    try:
      target_ip = self.ip_entry.get().strip()
      my_port = int(self.my_port_entry.get())
      send_port = int(self.send_port_entry.get())

      self.status_lbl.config(
          text=f"Статус: Підключення до {target_ip}:{send_port}...", fg="blue"
      )
      conn_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      conn_s.connect((target_ip, send_port))
      self.conn_send = conn_s

      server_recv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      server_recv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      server_recv.bind(("0.0.0.0", my_port))
      server_recv.listen(1)

      self.status_lbl.config(
          text=f"Статус: Очікування на порті {my_port}...", fg="blue"
      )
      conn_r, _ = server_recv.accept()
      self.conn_recv = conn_r
      server_recv.close()

      self.is_connected = True
      self.status_lbl.config(
          text=f"Статус: Повністю підключено до {target_ip}", fg="green"
      )
      self._start_io_loops()
    except Exception as e:
      self.status_lbl.config(text=f"Помилка: {e}", fg="red")
      self.handle_disconnect()

  def lock_ui(self):
    self.btn_listen.config(state=tk.DISABLED)
    self.btn_connect.config(state=tk.DISABLED)
    self.ip_entry.config(state=tk.DISABLED)
    self.my_port_entry.config(state=tk.DISABLED)
    self.send_port_entry.config(state=tk.DISABLED)
    self.btn_swap.config(state=tk.DISABLED)

  def unlock_ui(self):
    self.is_connected = False
    self.btn_listen.config(state=tk.NORMAL)
    self.btn_connect.config(state=tk.NORMAL)
    self.ip_entry.config(state=tk.NORMAL)
    self.my_port_entry.config(state=tk.NORMAL)
    self.send_port_entry.config(state=tk.NORMAL)
    self.btn_swap.config(state=tk.NORMAL)

  def _start_io_loops(self):
    threading.Thread(target=self._send_loop, daemon=True).start()
    threading.Thread(target=self._receive_loop, daemon=True).start()

  def _send_loop(self):
    while self.is_connected and self.conn_send:
      try:
        frame = self.current_local_frame
        _, encoded = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50]
        )
        data = encoded.tobytes()

        self.conn_send.sendall(struct.pack("!I", len(data)) + data)
        time.sleep(0.03)
      except Exception:
        break
    self.handle_disconnect()

  def _receive_loop(self):
    while self.is_connected and self.conn_recv:
      try:
        raw_sz = self._recv_exact(4)
        if not raw_sz:
          break
        sz = struct.unpack("!I", raw_sz)[0]

        data = self._recv_exact(sz)
        if not data:
          break

        frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
          self.current_remote_frame = frame
      except Exception:
        break
    self.handle_disconnect()

  def _recv_exact(self, n):
    buf = bytearray()
    while len(buf) < n and self.is_connected and self.conn_recv:
      try:
        packet = self.conn_recv.recv(n - len(buf))
        if not packet:
          return None
        buf.extend(packet)
      except Exception:
        return None
    return buf if len(buf) == n else None

  def handle_disconnect(self):
    if (
        not self.is_connected
        and self.conn_send is None
        and self.conn_recv is None
    ):
      self.root.after(0, self.reset_ui)
      return

    self.is_connected = False
    try:
      if self.conn_send:
        self.conn_send.close()
    except:
      pass
    try:
      if self.conn_recv:
        self.conn_recv.close()
    except:
      pass
    self.conn_send = None
    self.conn_recv = None
    self.current_remote_frame = self.black_frame
    self.root.after(0, self.reset_ui)

  def reset_ui(self):
    self.status_lbl.config(text="Статус: З'єднання розірвано", fg="red")
    self.unlock_ui()

  def on_close(self):
    self.is_connected = False
    try:
      if self.conn_send:
        self.conn_send.close()
    except:
      pass
    try:
      if self.conn_recv:
        self.conn_recv.close()
    except:
      pass
    if self.has_camera:
      try:
        self.cap.release()
      except:
        pass
    self.root.destroy()


if __name__ == "__main__":
  root = tk.Tk()
  app = P2PWebcamApp(root)
  root.mainloop()
  