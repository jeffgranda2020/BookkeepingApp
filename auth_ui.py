import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import re
import database as db

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))


COMMON_PASSWORDS = {
    "password", "123456", "12345678", "qwerty", "abc123", "monkey", "master",
    "dragon", "login", "princess", "football", "shadow", "sunshine", "trustno1",
    "iloveyou", "batman", "access", "hello", "charlie", "donald", "password1",
    "qwerty123", "letmein", "welcome", "admin", "passw0rd", "p@ssword",
    "p@ssw0rd", "password123", "changeme", "12345", "1234567890", "baseball",
    "starwars", "whatever", "superman", "computer", "michael", "jennifer",
    "jordan", "hunter", "ranger", "buster", "soccer", "hockey", "george",
    "andrew", "harley", "thunder", "pepper", "ginger", "joshua", "summer",
    "abcdef", "abcdefg", "abcdefgh", "qwertyuiop", "asdfghjkl", "zxcvbnm",
    "1q2w3e4r", "q1w2e3r4", "aaa111", "abc1234", "test123", "pass123",
}

KEYBOARD_PATTERNS = [
    "qwerty", "asdfgh", "zxcvbn", "qazwsx", "123456", "654321",
    "abcdef", "fedcba", "111111", "aaaaaa",
]

SECURITY_QUESTIONS = [
    "What was the name of your first pet?",
    "What city were you born in?",
    "What is your mother's maiden name?",
    "What was the name of your elementary school?",
    "What is the name of the street you grew up on?",
    "What was the make of your first car?",
    "What is your favorite movie?",
    "What was your childhood nickname?",
    "What is the name of your favorite childhood friend?",
    "What is the middle name of your oldest sibling?",
    "What was the first concert you attended?",
    "What is your favorite sports team?",
]


def validate_password(password, username=""):
    errors = []
    if len(password) < 10:
        errors.append("At least 10 characters")
    if not re.search(r'[A-Z]', password):
        errors.append("At least one uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.append("At least one lowercase letter")
    if not re.search(r'[0-9]', password):
        errors.append("At least one number")
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`]', password):
        errors.append("At least one special character")
    if not errors:
        lower_pw = password.lower()
        stripped_pw = re.sub(r'[^a-z]', '', lower_pw)
        if lower_pw in COMMON_PASSWORDS or stripped_pw in COMMON_PASSWORDS:
            errors.append("Too common — choose something less predictable")
        elif username and len(username) >= 3 and username.lower() in lower_pw:
            errors.append("Cannot contain your username")
        else:
            for pattern in KEYBOARD_PATTERNS:
                if pattern in stripped_pw:
                    errors.append("Contains a keyboard pattern — too easy to guess")
                    break
            if not errors:
                if len(set(lower_pw)) < 5:
                    errors.append("Too repetitive — use more unique characters")
    return errors


class LoginWindow:
    def __init__(self):
        self.user_id = None
        self.root = tk.Tk()
        self.root.title("5StarBookKeeping - Login")
        self.root.geometry("420x560")
        self.root.resizable(False, False)

        icon_path = os.path.join(APP_DIR, "app_icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self._center_window()

        self.main_frame = ttk.Frame(self.root, padding=30)
        self.main_frame.pack(fill="both", expand=True)

        self._show_login()
        self.root.mainloop()

    def _center_window(self):
        self.root.update_idletasks()
        w = 420
        h = 560
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _clear_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def _show_login(self):
        self._clear_frame()

        ttk.Label(self.main_frame, text="5StarBookKeeping",
                  font=("Segoe UI", 18, "bold")).pack(pady=(10, 5))
        ttk.Label(self.main_frame, text="Sign in to your account",
                  font=("Segoe UI", 10)).pack(pady=(0, 25))

        ttk.Label(self.main_frame, text="Username:", font=("Segoe UI", 10)).pack(anchor="w")
        self.login_user = ttk.Entry(self.main_frame, width=35, font=("Segoe UI", 11))
        self.login_user.pack(pady=(2, 12), ipady=4)

        ttk.Label(self.main_frame, text="Password:", font=("Segoe UI", 10)).pack(anchor="w")
        self.login_pass = ttk.Entry(self.main_frame, width=35, show="*", font=("Segoe UI", 11))
        self.login_pass.pack(pady=(2, 5), ipady=4)

        self.show_pass_var = tk.BooleanVar()
        ttk.Checkbutton(self.main_frame, text="Show password",
                        variable=self.show_pass_var,
                        command=self._toggle_login_pass).pack(anchor="w", pady=(0, 15))

        self.login_error = ttk.Label(self.main_frame, text="", foreground="red",
                                     font=("Segoe UI", 9))
        self.login_error.pack(pady=(0, 5))

        ttk.Button(self.main_frame, text="Login", command=self._do_login,
                   width=20).pack(pady=(5, 8))

        forgot_lbl = ttk.Label(self.main_frame, text="Forgot Password?",
                               font=("Segoe UI", 9, "underline"), foreground="#1a73e8",
                               cursor="hand2")
        forgot_lbl.pack(pady=(0, 10))
        forgot_lbl.bind("<Button-1>", lambda e: self._show_forgot_username())

        sep_frame = ttk.Frame(self.main_frame)
        sep_frame.pack(fill="x", pady=10)
        ttk.Separator(sep_frame).pack(fill="x")

        ttk.Label(self.main_frame, text="Don't have an account?",
                  font=("Segoe UI", 9)).pack(pady=(10, 5))
        ttk.Button(self.main_frame, text="Create Account",
                   command=self._show_signup, width=20).pack()

        self.login_user.focus_set()
        self.login_pass.bind("<Return>", lambda e: self._do_login())

    def _toggle_login_pass(self):
        self.login_pass.config(show="" if self.show_pass_var.get() else "*")

    def _do_login(self):
        username = self.login_user.get().strip()
        password = self.login_pass.get()

        if not username or not password:
            self.login_error.config(text="Please enter username and password.")
            return

        user_id = db.verify_user(username, password)
        if user_id is None:
            self.login_error.config(text="Invalid username or password.")
            return

        self.user_id = user_id
        self.root.destroy()

    def _show_signup(self):
        self._clear_frame()

        ttk.Label(self.main_frame, text="Create Account",
                  font=("Segoe UI", 18, "bold")).pack(pady=(10, 5))
        ttk.Label(self.main_frame, text="Set up your login credentials",
                  font=("Segoe UI", 10)).pack(pady=(0, 20))

        ttk.Label(self.main_frame, text="Username:", font=("Segoe UI", 10)).pack(anchor="w")
        self.signup_user = ttk.Entry(self.main_frame, width=35, font=("Segoe UI", 11))
        self.signup_user.pack(pady=(2, 12), ipady=4)

        ttk.Label(self.main_frame, text="Password:", font=("Segoe UI", 10)).pack(anchor="w")
        self.signup_pass = ttk.Entry(self.main_frame, width=35, show="*", font=("Segoe UI", 11))
        self.signup_pass.pack(pady=(2, 12), ipady=4)

        ttk.Label(self.main_frame, text="Confirm Password:", font=("Segoe UI", 10)).pack(anchor="w")
        self.signup_confirm = ttk.Entry(self.main_frame, width=35, show="*", font=("Segoe UI", 11))
        self.signup_confirm.pack(pady=(2, 5), ipady=4)

        self.show_signup_var = tk.BooleanVar()
        ttk.Checkbutton(self.main_frame, text="Show password",
                        variable=self.show_signup_var,
                        command=self._toggle_signup_pass).pack(anchor="w", pady=(0, 5))

        req_frame = ttk.LabelFrame(self.main_frame, text="Password Requirements", padding=8)
        req_frame.pack(fill="x", pady=(5, 10))
        self.req_labels = {}
        requirements = [
            ("length", "At least 10 characters"),
            ("upper", "At least one uppercase letter"),
            ("lower", "At least one lowercase letter"),
            ("digit", "At least one number"),
            ("special", "At least one special character (!@#$%...)"),
            ("strength", "Not a common password or pattern"),
        ]
        for key, text in requirements:
            lbl = ttk.Label(req_frame, text=f"  {text}", font=("Segoe UI", 8), foreground="#888")
            lbl.pack(anchor="w")
            self.req_labels[key] = lbl

        self.signup_pass.bind("<KeyRelease>", self._update_requirements)

        self.signup_error = ttk.Label(self.main_frame, text="", foreground="red",
                                      font=("Segoe UI", 9), wraplength=350)
        self.signup_error.pack(pady=(0, 5))

        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill="x", pady=(5, 0))
        ttk.Button(btn_frame, text="Back to Login",
                   command=self._show_login).pack(side="left")
        ttk.Button(btn_frame, text="Create Account",
                   command=self._do_signup).pack(side="right")

        self.signup_user.focus_set()
        self.signup_confirm.bind("<Return>", lambda e: self._do_signup())

    def _toggle_signup_pass(self):
        show = "" if self.show_signup_var.get() else "*"
        self.signup_pass.config(show=show)
        self.signup_confirm.config(show=show)

    def _update_requirements(self, event=None):
        password = self.signup_pass.get()
        username = self.signup_user.get().strip()
        checks = {
            "length": len(password) >= 10,
            "upper": bool(re.search(r'[A-Z]', password)),
            "lower": bool(re.search(r'[a-z]', password)),
            "digit": bool(re.search(r'[0-9]', password)),
            "special": bool(re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`]', password)),
            "strength": len(password) >= 10 and not validate_password(password, username),
        }
        for key, passed in checks.items():
            self.req_labels[key].config(foreground="#2e7d32" if passed else "#888")

    def _do_signup(self):
        username = self.signup_user.get().strip()
        password = self.signup_pass.get()
        confirm = self.signup_confirm.get()

        if not username:
            self.signup_error.config(text="Username is required.")
            return

        if len(username) < 3:
            self.signup_error.config(text="Username must be at least 3 characters.")
            return

        errors = validate_password(password, username)
        if errors:
            self.signup_error.config(text="Password: " + ", ".join(errors))
            return

        if password != confirm:
            self.signup_error.config(text="Passwords do not match.")
            return

        self._pending_username = username
        self._pending_password = password
        self._show_security_questions_setup()

    def _show_security_questions_setup(self):
        self._clear_frame()
        self.root.geometry("480x580")

        ttk.Label(self.main_frame, text="Security Questions",
                  font=("Segoe UI", 16, "bold")).pack(pady=(5, 3))
        ttk.Label(self.main_frame, text="Choose 3 questions in case you forget your password.",
                  font=("Segoe UI", 9)).pack(pady=(0, 12))

        self._sq_combos = []
        self._sq_answers = []

        for i in range(3):
            ttk.Label(self.main_frame, text=f"Question {i + 1}:",
                      font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 0))
            combo = ttk.Combobox(self.main_frame, values=SECURITY_QUESTIONS,
                                 state="readonly", width=50, font=("Segoe UI", 9))
            combo.pack(anchor="w", pady=(2, 2))
            if i < len(SECURITY_QUESTIONS):
                combo.current(i)
            self._sq_combos.append(combo)

            ans = ttk.Entry(self.main_frame, width=42, font=("Segoe UI", 10))
            ans.pack(anchor="w", pady=(2, 4), ipady=3)
            self._sq_answers.append(ans)

        self._sq_error = ttk.Label(self.main_frame, text="", foreground="red",
                                    font=("Segoe UI", 9), wraplength=420)
        self._sq_error.pack(pady=(8, 5))

        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill="x", pady=(5, 0))
        ttk.Button(btn_frame, text="Back",
                   command=self._show_signup).pack(side="left")
        ttk.Button(btn_frame, text="Finish Setup",
                   command=self._finish_signup).pack(side="right")

        self._sq_answers[0].focus_set()

    def _finish_signup(self):
        questions_chosen = [c.get() for c in self._sq_combos]
        answers = [a.get().strip() for a in self._sq_answers]

        if len(set(questions_chosen)) < 3:
            self._sq_error.config(text="Please choose 3 different questions.")
            return

        for i, ans in enumerate(answers):
            if not ans:
                self._sq_error.config(text=f"Please answer all 3 questions.")
                return
            if len(ans) < 2:
                self._sq_error.config(text=f"Answer {i + 1} is too short.")
                return

        user_id = db.create_user(self._pending_username, self._pending_password)
        if user_id is None:
            self._sq_error.config(text="Username already taken. Go back and choose another.")
            return

        qa_pairs = list(zip(questions_chosen, answers))
        db.save_security_questions(user_id, qa_pairs)

        self.root.geometry("420x560")

        if db.get_user_count() == 1 and db.has_legacy_data():
            self._ask_legacy_data(user_id)
        else:
            db.seed_defaults_for_user(user_id)
            messagebox.showinfo("Success", "Account created! You can now log in.")
            self._show_login()

    def _ask_legacy_data(self, user_id):
        self._clear_frame()

        ttk.Label(self.main_frame, text="Existing Data Found",
                  font=("Segoe UI", 16, "bold")).pack(pady=(20, 10))

        ttk.Label(self.main_frame,
                  text="We found data from before the login system was added.\n"
                       "Would you like to import this existing data into\n"
                       "your new account, or start fresh?",
                  font=("Segoe UI", 10), justify="center").pack(pady=(10, 30))

        ttk.Button(self.main_frame, text="Import Existing Data Into My Account",
                   command=lambda: self._handle_legacy(user_id, adopt=True),
                   width=35).pack(pady=8)

        ttk.Button(self.main_frame, text="Start Fresh (Empty Account)",
                   command=lambda: self._handle_legacy(user_id, adopt=False),
                   width=35).pack(pady=8)

    def _handle_legacy(self, user_id, adopt):
        if adopt:
            db.adopt_legacy_data(user_id)
            messagebox.showinfo("Success", "Existing data has been imported into your account.\nYou can now log in.")
        else:
            db.seed_defaults_for_user(user_id)
            messagebox.showinfo("Success", "Account created with a fresh start.\nYou can now log in.")
        self._show_login()

    # ─── Forgot Password Flow ───

    def _show_forgot_username(self):
        self._clear_frame()
        self.root.geometry("420x560")

        ttk.Label(self.main_frame, text="Reset Password",
                  font=("Segoe UI", 16, "bold")).pack(pady=(20, 5))
        ttk.Label(self.main_frame, text="Enter your username to retrieve your security questions.",
                  font=("Segoe UI", 9)).pack(pady=(0, 20))

        ttk.Label(self.main_frame, text="Username:", font=("Segoe UI", 10)).pack(anchor="w")
        self._forgot_user_entry = ttk.Entry(self.main_frame, width=35, font=("Segoe UI", 11))
        self._forgot_user_entry.pack(pady=(2, 12), ipady=4)

        self._forgot_error = ttk.Label(self.main_frame, text="", foreground="red",
                                        font=("Segoe UI", 9))
        self._forgot_error.pack(pady=(0, 10))

        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text="Back to Login",
                   command=self._show_login).pack(side="left")
        ttk.Button(btn_frame, text="Next",
                   command=self._forgot_lookup_user).pack(side="right")

        self._forgot_user_entry.focus_set()
        self._forgot_user_entry.bind("<Return>", lambda e: self._forgot_lookup_user())

    def _forgot_lookup_user(self):
        username = self._forgot_user_entry.get().strip()
        if not username:
            self._forgot_error.config(text="Please enter your username.")
            return

        result = db.get_security_questions(username)
        if result is None:
            self._forgot_error.config(text="No account found or no security questions set.")
            return

        self._reset_user_id, questions_data = result
        self._reset_username = username
        self._reset_questions = [(q, h, s) for q, h, s in questions_data]
        self._show_forgot_answers()

    def _show_forgot_answers(self):
        self._clear_frame()
        self.root.geometry("480x520")

        ttk.Label(self.main_frame, text="Answer Security Questions",
                  font=("Segoe UI", 16, "bold")).pack(pady=(10, 5))
        ttk.Label(self.main_frame, text="Answer all 3 questions correctly to reset your password.",
                  font=("Segoe UI", 9)).pack(pady=(0, 15))

        self._forgot_answers = []
        for i, (question, _, _) in enumerate(self._reset_questions):
            ttk.Label(self.main_frame, text=question,
                      font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
            ans = ttk.Entry(self.main_frame, width=42, font=("Segoe UI", 10))
            ans.pack(anchor="w", pady=(2, 2), ipady=3)
            self._forgot_answers.append(ans)

        self._forgot_ans_error = ttk.Label(self.main_frame, text="", foreground="red",
                                            font=("Segoe UI", 9), wraplength=420)
        self._forgot_ans_error.pack(pady=(10, 5))

        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text="Back to Login",
                   command=self._show_login).pack(side="left")
        ttk.Button(btn_frame, text="Verify",
                   command=self._verify_security_answers).pack(side="right")

        self._forgot_answers[0].focus_set()

    def _verify_security_answers(self):
        answers = [a.get().strip() for a in self._forgot_answers]
        for ans in answers:
            if not ans:
                self._forgot_ans_error.config(text="Please answer all questions.")
                return

        if not db.verify_security_answers(self._reset_user_id, answers):
            self._forgot_ans_error.config(text="One or more answers are incorrect. Try again.")
            return

        self._show_reset_password()

    def _show_reset_password(self):
        self._clear_frame()
        self.root.geometry("420x560")

        ttk.Label(self.main_frame, text="Set New Password",
                  font=("Segoe UI", 16, "bold")).pack(pady=(20, 5))
        ttk.Label(self.main_frame, text="Choose a new password for your account.",
                  font=("Segoe UI", 9)).pack(pady=(0, 20))

        ttk.Label(self.main_frame, text="New Password:", font=("Segoe UI", 10)).pack(anchor="w")
        self._reset_pass = ttk.Entry(self.main_frame, width=35, show="*", font=("Segoe UI", 11))
        self._reset_pass.pack(pady=(2, 12), ipady=4)

        ttk.Label(self.main_frame, text="Confirm New Password:", font=("Segoe UI", 10)).pack(anchor="w")
        self._reset_confirm = ttk.Entry(self.main_frame, width=35, show="*", font=("Segoe UI", 11))
        self._reset_confirm.pack(pady=(2, 5), ipady=4)

        self._show_reset_var = tk.BooleanVar()
        ttk.Checkbutton(self.main_frame, text="Show password",
                        variable=self._show_reset_var,
                        command=self._toggle_reset_pass).pack(anchor="w", pady=(0, 5))

        req_frame = ttk.LabelFrame(self.main_frame, text="Password Requirements", padding=8)
        req_frame.pack(fill="x", pady=(5, 10))
        self._reset_req_labels = {}
        requirements = [
            ("length", "At least 10 characters"),
            ("upper", "At least one uppercase letter"),
            ("lower", "At least one lowercase letter"),
            ("digit", "At least one number"),
            ("special", "At least one special character (!@#$%...)"),
            ("strength", "Not a common password or pattern"),
        ]
        for key, text in requirements:
            lbl = ttk.Label(req_frame, text=f"  {text}", font=("Segoe UI", 8), foreground="#888")
            lbl.pack(anchor="w")
            self._reset_req_labels[key] = lbl

        self._reset_pass.bind("<KeyRelease>", self._update_reset_requirements)

        self._reset_error = ttk.Label(self.main_frame, text="", foreground="red",
                                       font=("Segoe UI", 9), wraplength=350)
        self._reset_error.pack(pady=(5, 5))

        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill="x", pady=(5, 0))
        ttk.Button(btn_frame, text="Back to Login",
                   command=self._show_login).pack(side="left")
        ttk.Button(btn_frame, text="Reset Password",
                   command=self._do_reset_password).pack(side="right")

        self._reset_pass.focus_set()

    def _toggle_reset_pass(self):
        show = "" if self._show_reset_var.get() else "*"
        self._reset_pass.config(show=show)
        self._reset_confirm.config(show=show)

    def _update_reset_requirements(self, event=None):
        password = self._reset_pass.get()
        checks = {
            "length": len(password) >= 10,
            "upper": bool(re.search(r'[A-Z]', password)),
            "lower": bool(re.search(r'[a-z]', password)),
            "digit": bool(re.search(r'[0-9]', password)),
            "special": bool(re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`]', password)),
            "strength": len(password) >= 10 and not validate_password(password, self._reset_username),
        }
        for key, passed in checks.items():
            self._reset_req_labels[key].config(foreground="#2e7d32" if passed else "#888")

    def _do_reset_password(self):
        password = self._reset_pass.get()
        confirm = self._reset_confirm.get()

        errors = validate_password(password, self._reset_username)
        if errors:
            self._reset_error.config(text="Password: " + ", ".join(errors))
            return

        if password != confirm:
            self._reset_error.config(text="Passwords do not match.")
            return

        success = db.reset_password(self._reset_user_id, password)
        if not success:
            self._reset_error.config(text="New password cannot be the same as your old password.")
            return

        messagebox.showinfo("Success", "Password has been reset! You can now log in.")
        self._show_login()
