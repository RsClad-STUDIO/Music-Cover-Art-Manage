def get_stylesheet(is_dark):
    """A restrained Windows 10-style palette with compact, mostly square controls."""
    if is_dark:
        bg, panel, field, fg, muted, border, accent = (
            "#202020", "#202020", "#2b2b2b", "#f3f3f3",
            "#b8b8b8", "#454545", "#0078d4"
        )
        hover, button_fg, disabled = "#383838", "#f3f3f3", "#777777"
    else:
        bg, panel, field, fg, muted, border, accent = (
            "#f3f3f3", "#f3f3f3", "#ffffff", "#1b1b1b",
            "#606060", "#c8c8c8", "#0078d4"
        )
        hover, button_fg, disabled = "#e5e5e5", "#1b1b1b", "#999999"

    return f"""
        QWidget {{
            background-color: {bg};
            color: {fg};
            font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
            font-size: 9pt;
        }}
        QMainWindow {{ background-color: {bg}; }}
        QLabel {{ background: transparent; }}
        QLabel#PageTitle {{ font-size: 15pt; font-weight: 600; }}
        QLabel#SectionTitle {{ font-size: 9pt; font-weight: 600; }}
        QLabel#Muted {{ color: {muted}; }}

        QFrame#Panel {{
            background-color: {panel};
            border: 1px solid {border};
            border-radius: 2px;
        }}

        QLineEdit, QPlainTextEdit {{
            background-color: {field};
            color: {fg};
            border: 1px solid {border};
            border-radius: 2px;
            padding: 4px 6px;
            selection-background-color: {accent};
        }}
        QLineEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {accent};
        }}

        QPushButton {{
            background-color: {field};
            color: {button_fg};
            border: 1px solid {border};
            border-radius: 2px;
            padding: 5px 10px;
            font-weight: 400;
        }}
        QPushButton:hover {{ background-color: {hover}; }}
        QPushButton:pressed {{
            background-color: {accent};
            color: white;
        }}
        QPushButton:disabled {{
            color: {disabled};
            background-color: {panel};
        }}
        QPushButton#Primary {{
            background-color: {accent};
            color: white;
            border: 1px solid {accent};
        }}
        QPushButton#Primary:hover {{ background-color: #006cbe; }}
        QPushButton#Primary:pressed {{ background-color: #005a9e; }}

        QProgressBar {{
            background-color: {field};
            border: 1px solid {border};
            border-radius: 1px;
            min-height: 14px;
            max-height: 14px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {accent};
            border-radius: 0px;
        }}

        QPlainTextEdit#Log {{
            background-color: {field};
            border: 1px solid {border};
            border-radius: 2px;
            padding: 5px;
            font-family: "Cascadia Mono", "Consolas", monospace;
            font-size: 9pt;
        }}
    """
