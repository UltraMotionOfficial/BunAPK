"""Read versionCode / versionName from an APK's binary AndroidManifest.xml.

Android ships ``AndroidManifest.xml`` inside the APK as Android Binary XML
(AXML), not text. This module decodes just enough of the AXML chunk format —
the string pool and the ``<manifest>`` start element — to recover the version
attributes, with no external dependencies.
"""

from __future__ import annotations

import struct
import zipfile
from pathlib import Path
from typing import Optional

# AXML chunk-type magic numbers
_AXML_MAGIC = 0x00080003
_CHUNK_STRING_POOL = 0x0001
_CHUNK_START_ELEMENT = 0x0102
_FLAG_UTF8 = 0x00000100


def read_apk_version(apk_path: Path | str) -> tuple[Optional[int], Optional[str]]:
    """Return ``(versionCode, versionName)`` for *apk_path*.

    Either value may be ``None`` if the APK can't be read or parsed.
    """
    version_code: Optional[int] = None
    version_name: Optional[str] = None

    try:
        with zipfile.ZipFile(apk_path) as zf:
            if "AndroidManifest.xml" not in zf.namelist():
                return None, None
            data = zf.read("AndroidManifest.xml")
    except Exception:
        return None, None

    try:
        magic = struct.unpack("<I", data[:4])[0]
        if magic != _AXML_MAGIC:
            return None, None

        offset = 8

        sp_type, sp_header_size, sp_chunk_size = struct.unpack("<HHI", data[offset:offset + 8])
        if sp_type != _CHUNK_STRING_POOL:
            return None, None

        sp_data = data[offset:offset + sp_chunk_size]
        offset += sp_chunk_size

        string_count, _, flags, string_offset_table, _ = struct.unpack("<IIIII", sp_data[8:28])
        is_utf8 = bool(flags & _FLAG_UTF8)

        offsets = []
        for i in range(string_count):
            start = 28 + i * 4
            offsets.append(struct.unpack("<I", sp_data[start:start + 4])[0])

        strings = []
        raw_strings_start = string_offset_table
        for off in offsets:
            str_start = raw_strings_start + off
            if is_utf8:
                l1 = sp_data[str_start]
                if l1 & 0x80:
                    str_start += 2
                else:
                    str_start += 1
                l2 = sp_data[str_start]
                if l2 & 0x80:
                    str_start += 2
                    byte_len = ((l2 & 0x7F) << 8) | sp_data[str_start - 1]
                else:
                    str_start += 1
                    byte_len = l2

                s_bytes = sp_data[str_start:str_start + byte_len]
                strings.append(s_bytes.decode("utf-8", errors="ignore"))
            else:
                l1 = struct.unpack("<H", sp_data[str_start:str_start + 2])[0]
                if l1 & 0x8000:
                    str_start += 4
                    char_len = ((l1 & 0x7FFF) << 16) | struct.unpack("<H", sp_data[str_start - 2:str_start])[0]
                else:
                    str_start += 2
                    char_len = l1
                byte_len = char_len * 2
                s_bytes = sp_data[str_start:str_start + byte_len]
                strings.append(s_bytes.decode("utf-16", errors="ignore"))

        while offset < len(data):
            chunk_type, header_size, chunk_size = struct.unpack("<HHI", data[offset:offset + 8])
            if chunk_type == _CHUNK_START_ELEMENT:
                element_data = data[offset:offset + chunk_size]
                name_idx = struct.unpack("<I", element_data[20:24])[0]
                if name_idx < len(strings) and strings[name_idx] == "manifest":
                    attr_start = struct.unpack("<H", element_data[24:26])[0]
                    attr_size = struct.unpack("<H", element_data[26:28])[0]
                    attr_count = struct.unpack("<H", element_data[28:30])[0]

                    for a_idx in range(attr_count):
                        start_a = header_size + attr_start + a_idx * attr_size
                        a_ns_idx, a_name_idx, a_val_idx, a_size, a_res, a_type, a_data = struct.unpack(
                            "<IIIHBBI", element_data[start_a:start_a + 20]
                        )
                        if a_name_idx < len(strings):
                            name_str = strings[a_name_idx]
                            if name_str == "versionCode":
                                version_code = int(a_data)
                            elif name_str == "versionName":
                                if a_val_idx != 0xFFFFFFFF and a_val_idx < len(strings):
                                    version_name = strings[a_val_idx]
            offset += chunk_size
    except Exception:
        pass

    return version_code, version_name
