def test_gui_modules_import_with_pinned_qt_dependency():
    from music_cover_art_manage import gui, gui_worker

    assert gui.MainWindow is not None
    assert gui_worker.WorkerThread is not None
