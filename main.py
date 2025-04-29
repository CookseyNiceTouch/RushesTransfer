import os
import sys
from app import RushesTransferApp
import customtkinter as ctk

# Set appearance mode and default color theme
ctk.set_appearance_mode("dark")  # Options: "Dark", "Light", "System"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"

def main():
    root = ctk.CTk()
    app = RushesTransferApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
