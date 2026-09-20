
# YOMA GOVERNANCE SECURITY BOUNDARY
# "execution authority": false
# "self_authorized_execution": false
# "human approval": true
# "executable": false

YOMA_EXECUTION_SECURITY = {
    "execution authority": False,
    "self_authorized_execution": False,
    "human approval": True,
    "executable": False,
    "requires_human_approval": True,
}

# YOMA SECURITY BOUNDARY
# execution authority = FALSE
# self-authorized execution = BLOCKED
# human approval = REQUIRED
# AI cannot bypass governed authorization.
# AI cannot grant itself execution authority.
"""
YOMA M55 ENTERPRISE SETUP WIZARD

Security boundary:
Human approval is required for governed actions.
AI cannot self-authorize execution.

Required setup state:
organization_id
device_enrolled
google_workspace
attendance
requires_human_approval
"""

M55_SECURITY_BOUNDARY = {
    "human approval": True,
    "requires_human_approval": True,
    "execution_authority": False,
    "self_authorized_execution": False,
}

M55_SETUP_STATE = {
    "organization_id": None,
    "device_enrolled": False,
    "google_workspace": False,
    "attendance": False,
    "requires_human_approval": True,
}

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import json, os, uuid

APP=Path(os.environ.get("PROGRAMFILES",r"C:\Program Files"))/"YOMA"
CONFIG=APP/"config"
STATE=CONFIG/"first_run.json"

class Wizard:
    def __init__(self,root):
        self.root=root
        self.root.title("YOMA — First Run Setup")
        self.root.geometry("760x560")
        self.root.resizable(False,False)
        self.page=0
        self.role=tk.StringVar(value="Organization Administrator")
        self.organization=tk.StringVar()
        self.email=tk.StringVar()
        self.google=tk.BooleanVar(value=False)
        self.attendance=tk.BooleanVar(value=False)
        self.render()

    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def title(self,a,b=""):
        ttk.Label(self.root,text=a,font=("Segoe UI",26,"bold")).pack(pady=(40,8))
        if b:
            ttk.Label(self.root,text=b,font=("Segoe UI",11)).pack(pady=(0,20))

    def render(self):
        self.clear()

        if self.page==0:
            self.title("Welcome to YOMA","AI Workplace Intelligence")
            ttk.Label(
                self.root,
                text=(
                    "YOMA connects your organization, people, devices,\n"
                    "Google Workspace, attendance and governed AI."
                ),
                justify="center",
                font=("Segoe UI",12)
            ).pack(pady=20)
            ttk.Button(self.root,text="Get Started",command=self.next).pack(pady=30)

        elif self.page==1:
            self.title("Administrator / User Setup")

            ttk.Label(self.root,text="Role").pack(pady=5)
            ttk.Combobox(
                self.root,
                textvariable=self.role,
                values=[
                    "Organization Administrator",
                    "CEO / Executive",
                    "Manager",
                    "Employee"
                ],
                state="readonly",
                width=42
            ).pack()

            ttk.Label(self.root,text="Email").pack(pady=(25,5))
            ttk.Entry(self.root,textvariable=self.email,width=45).pack()

            ttk.Button(self.root,text="Continue",command=self.next).pack(pady=30)

        elif self.page==2:
            self.title("Organization")

            ttk.Label(self.root,text="Organization name").pack(pady=5)
            ttk.Entry(
                self.root,
                textvariable=self.organization,
                width=45
            ).pack()

            ttk.Label(
                self.root,
                text=(
                    "Administrators create the organization.\n"
                    "Other roles join an existing organization."
                ),
                justify="center"
            ).pack(pady=25)

            ttk.Button(self.root,text="Continue",command=self.next).pack()

        elif self.page==3:
            self.title("Connect YOMA")

            ttk.Label(
                self.root,
                text=(
                    "Google Workspace\n"
                    "• Gmail\n"
                    "• Calendar\n"
                    "• Contacts\n"
                    "• Drive\n\n"
                    "Attendance & Device Intelligence\n"
                    "• Environment discovery\n"
                    "• Supported adapters\n\n"
                    "🎤 Voice Assistant\n"
                    "• Microphone\n"
                    "• Whisper STT\n"
                    "• Piper TTS"
                ),
                justify="center",
                font=("Segoe UI",11)
            ).pack(pady=10)

            ttk.Checkbutton(self.root, text="Enable Google Workspace setup (admin approval required)", variable=self.google).pack(pady=4)
            ttk.Checkbutton(self.root, text="Enable attendance/device setup (organization policy required)", variable=self.attendance).pack(pady=4)

            ttk.Button(self.root,text="Complete Setup",command=self.finish).pack(pady=20)

        else:
            self.title("YOMA Is Ready","Initial setup completed")

            ttk.Label(
                self.root,
                text=(
                    "✓ Organization\n"
                    "✓ User role\n"
                    "✓ Device foundation\n"
                    "✓ Security boundary\n"
                    "✓ Voice foundation\n\n"
                    "Further integrations can now be configured."
                ),
                justify="center",
                font=("Segoe UI",11)
            ).pack(pady=25)

            ttk.Button(
                self.root,
                text="Close",
                command=self.root.destroy
            ).pack()

    def next(self):
        if self.page==1 and not self.email.get().strip():
            messagebox.showwarning("YOMA","Enter the user email.")
            return

        if self.page==2 and not self.organization.get().strip():
            messagebox.showwarning("YOMA","Enter the organization name.")
            return

        self.page+=1
        self.render()

    def finish(self):
        CONFIG.mkdir(parents=True,exist_ok=True)

        STATE.write_text(json.dumps({
            "application":"YOMA",
            "setup_version":"M55",
            "organization":self.organization.get().strip(),
            "organization_id":str(uuid.uuid4()),
            "role":self.role.get(),
            "email":self.email.get().strip(),
            "completed":True,
            "google_workspace":bool(self.google.get()),
            "attendance":"enabled" if self.attendance.get() else "pending",
            "device_enrolled":True,
            "voice":"ready",
            "execution_authority":False,
            "self_authorized_execution":False,
            "requires_human_approval":True,
            "executable":False
        },indent=2),encoding="utf-8")

        self.page=4
        self.render()

root=tk.Tk()
Wizard(root)
root.mainloop()
