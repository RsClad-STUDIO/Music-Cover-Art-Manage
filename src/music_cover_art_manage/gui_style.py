def get_stylesheet(is_dark):
    if is_dark:
        bg, panel, field, fg, muted, border, accent = ("#17191f", "#22252d", "#2b2f39", "#f1f3f8", "#a2a9b8", "#3a3f4b", "#7c8cff")
        hover, button_fg = "#343947", "#f1f3f8"
    else:
        bg, panel, field, fg, muted, border, accent = ("#f3f5f9", "#ffffff", "#f7f8fb", "#202534", "#697386", "#dce1ea", "#536dfe")
        hover, button_fg = "#e9edf5", "#202534"
    return f"""
        QWidget {{ background-color: {bg}; color: {fg}; font-family: "Segoe UI", "Yu Gothic UI", sans-serif; font-size: 10pt; }}
        QMainWindow {{ background-color: {bg}; }}
        QLabel {{ background: transparent; }}
        QLabel#PageTitle {{ font-size: 20pt; font-weight: 700; }}
        QLabel#SectionTitle {{ font-size: 11pt; font-weight: 650; }}
        QLabel#Muted {{ color: {muted}; }}
        QFrame#Panel {{ background-color: {panel}; border: 1px solid {border}; border-radius: 12px; }}
        QLineEdit, QPlainTextEdit {{ background-color: {field}; color: {fg}; border: 1px solid {border}; border-radius: 7px; padding: 8px; selection-background-color: {accent}; }}
        QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {accent}; }}
        QPushButton {{ background-color: {field}; color: {button_fg}; border: 1px solid {border}; border-radius: 7px; padding: 9px 15px; font-weight: 600; }}
        QPushButton:hover {{ background-color: {hover}; }}
        QPushButton:disabled {{ color: {muted}; background-color: {panel}; }}
        QPushButton#Primary {{ background-color: {accent}; color: white; border: 1px solid {accent}; }}
        QPushButton#Primary:hover {{ background-color: #6678f5; }}
        QProgressBar {{ background-color: {field}; border: 0; border-radius: 5px; min-height: 10px; max-height: 10px; text-align: center; }}
        QProgressBar::chunk {{ background-color: {accent}; border-radius: 5px; }}
        QPlainTextEdit#Log {{ background-color: {field}; border: 1px solid {border}; border-radius: 8px; padding: 10px; font-family: "Cascadia Mono", "Consolas", monospace; font-size: 9pt; }}
    """
