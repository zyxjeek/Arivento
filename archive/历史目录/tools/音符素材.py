"""生成不透明的青色音符PNG，带白色顶边。仅使用Python标准库。"""
import struct
import zlib


def 生成(路径):
    宽, 高 = 64, 16
    def 数据块(类型, 内容):
        return struct.pack('>I', len(内容)) + 类型 + 内容 + struct.pack('>I', zlib.crc32(类型 + 内容))
    像素 = b''.join(b'\0' + bytes((234, 242, 255, 255) if 行 < 2 else (86, 222, 239, 255)) * 宽 for 行 in range(高))
    图片 = b'\x89PNG\r\n\x1a\n' + 数据块(b'IHDR', struct.pack('>IIBBBBB', 宽, 高, 8, 6, 0, 0, 0))
    路径.parent.mkdir(parents=True, exist_ok=True)
    路径.write_bytes(图片 + 数据块(b'IDAT', zlib.compress(像素)) + 数据块(b'IEND', b''))
