def get_stylesheet(is_dark):
    if is_dark:
        bg = "#111318"
        panel = "#1b1e25"
        field = "#12151b"
        fg = "#e8eaf0"
        muted = "#a1a8b5"
        border = "#343a46"
        accent = "#7c9cff"
        accent_hover = "#91aaff"
        log_bg = "#0d1015"
    else:
        bg = "#f4f6fa"
        panel = "#ffffff"
        field = "#f8f9fc"
        fg = "#202532"
        muted = "#687184"
        border = "#dce1ea"
        accent = "#315fce"
        accent_hover = "#244fb6"
        log_bg = "#fbfcfe"

    return f"""
        QWidget {{
            color: {fg};
            font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
            font-size: 10pt;
        }}
        QMainWindow, #WindowRoot {{
            background-color: {bg};
        }}
        #PageTitle {{
            font-size: 20pt;
            font-weight: 650;
            color: {fg};
        }}
        #Subtitle, #FieldLabel {{
            color: {muted};
        }}
        #FieldLabel {{
            font-weight: 600;
            margin-bottom: 2px;
        }}
        #SectionTitle {{
            font-size: 11pt;
            font-weight: 650;
        }}
        #StatusLabel {{
            color: {muted};
            font-weight: 600;
        }}
        #Card {{
            background-color: {panel};
            border: 1px solid {border};
            border-radius: 12px;
        }}
        QLineEdit {{
            background-color: {field};
            color: {fg};
            border: 1px solid {border};
            border-radius: 7px;
            padding: 10px 12px;
            selection-background-color: {accent};
        }}
        QLineEdit:focus {{
            border: 1px solid {accent};
        }}
        QPushButton {{
            background-color: {panel};
            color: {fg};
            border: 1px solid {border};
            border-radius: 7px;
            padding: 9px 16px;
            min-height: 18px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            border-color: {accent};
        }}
        QPushButton:pressed {{
            background-color: {field};
        }}
        QPushButton:disabled {{
            color: {muted};
            background-color: {field};
            border-color: {border};
        }}
        #PrimaryButton {{
            background-color: {panel};
        }}
        #AccentButton {{
            background-color: {accent};
            color: #ffffff;
            border-color: {accent};
        }}
        #AccentButton:hover {{
            background-color: {accent_hover};
            border-color: {accent_hover};
        }}
        #QuietButton {{
            background: transparent;
            border-color: transparent;
            color: {muted};
        }}
        QProgressBar {{
            background-color: {field};
            border: 1px solid {border};
            border-radius: 6px;
            min-height: 12px;
            max-height: 12px;
            text-align: center;
            color: {muted};
        }}
        QProgressBar::chunk {{
            background-color: {accent};
            border-radius: 5px;
        }}
        #LogView {{
            background-color: {log_bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 9px;
            padding: 12px;
            font-family: "Cascadia Mono", "Consolas", monospace;
            font-size: 9pt;
            selection-background-color: {accent};
        }}
        QScrollBar:vertical {{
            background: {field};
            width: 12px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {border};
            min-height: 28px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
    """
