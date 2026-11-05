def test_gui_modules_import_with_pinned_qt_dependency():
    import gui_main
    import gui_worker

    assert gui_main.MainWindow is not None
    assert gui_worker.WorkerThread is not None
