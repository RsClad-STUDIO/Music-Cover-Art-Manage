from processor import fit_to_width


def test_fit_to_width_keeps_east_asian_characters_aligned():
    assert fit_to_width("ABC日本語", 7) == "ABC日本  "


def test_fit_to_width_handles_long_strings_and_zero_width():
    assert fit_to_width("abcdefgh", 4) == "abcd"
    assert fit_to_width("abc", 0) == ""
