def get_stylesheet(is_dark):
    bg, fg, card, accent = ("#1e1e1e", "#ffffff", "#2d2d2d", "#3d5afe") if is_dark else ("#f5f5f5", "#000000", "#ffffff", "#2979ff")
    return f"""
        QMainWindow {{ background-color: {bg}; color: {fg}; }}
        QLabel {{ color: {fg}; }}
        QLineEdit {{ background-color: {card}; color: {fg}; border: 1px solid #555; padding: 8px; }}
        QPushButton {{ background-color: {card}; color: {fg}; padding: 8px 15px; }}
        #Card {{ background-color: {card}; border-radius: 10px; }}
        QProgressBar {{ background-color: {card}; border-radius: 5px; }}
        QProgressBar::chunk {{ background-color: {accent}; }}
    """
