from processor import fit_to_width


def test_fit_to_width_keeps_east_asian_characters_aligned():
    assert fit_to_width("ABC日本語", 7) == "ABC日本"


def test_fit_to_width_handles_long_strings_and_zero_width():
    assert fit_to_width("abcdefgh", 4) == "abcd"
    assert fit_to_width("abc", 0) == ""


def test_mp3_artwork_update_preserves_picture_metadata(tmp_path):
    from mutagen.id3 import APIC, ID3
    from processor import ImageInfo, update_audio_images

    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"")
    image = ImageInfo(b"not-a-real-jpeg", "image/jpeg", 3, "Front cover", "hash")

    update_audio_images(audio_path, [image])

    tags = ID3(str(audio_path))
    pictures = [frame for frame in tags.values() if isinstance(frame, APIC)]
    assert len(pictures) == 1
    assert pictures[0].mime == "image/jpeg"
    assert pictures[0].desc == "Front cover"
    assert pictures[0].type == 3
