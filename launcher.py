import customtkinter as ctk
import sys
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class JarvisLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JARVIS SYSTEM BOOTLOADER")
        self.geometry("500x350")
        self.selected_model = None

        self.label = ctk.CTkLabel(self, text="SELECT NEURAL PATHWAY", font=("Roboto Medium", 18))
        self.label.pack(pady=20)

        # 1. 主力：Gemini 2.5 Flash (你测出来是 Alive 的)
        self.btn_main = ctk.CTkButton(self, text="PROTOCOL: PHOENIX (Gemini 2.5 Flash)\n[Status: ALIVE | Primary]", 
                                      command=lambda: self.select_model("gemini-2.5-flash"),
                                      height=60, width=320, fg_color="#2ECC71", hover_color="#27AE60")
        self.btn_main.pack(pady=15)

        # 2. 重火器：Gemini 3 Flash (每天 20 次)
        self.btn_heavy = ctk.CTkButton(self, text="PROTOCOL: OMNI (Gemini 3 Flash)\n[Status: Limit 20/day]", 
                                       command=lambda: self.select_model("gemini-3-flash-preview"),
                                       height=60, width=320, fg_color="#C0392B", hover_color="#922B21")
        self.btn_heavy.pack(pady=15)

        self.status = ctk.CTkLabel(self, text="System Standby...", text_color="gray")
        self.status.pack(pady=20)

    def select_model(self, model_id):
        self.selected_model = model_id
        self.status.configure(text=f"Engaging {model_id}...", text_color="#3498DB")
        self.update()
        self.after(500, self.destroy)

def get_user_selection():
    app = JarvisLauncher()
    app.mainloop()
    return app.selected_model

if __name__ == "__main__":
    print(get_user_selection())