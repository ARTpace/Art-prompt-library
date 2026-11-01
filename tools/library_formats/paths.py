DETAIL_PREFIX = "detail-"
DETAIL_FIELDS = ("tags", "img_url", "danbooru_url")
THUMB_BASE = "https://blobs.animadex.net/Outputs/thumbs/"

def detail_shard_of(char_id: str) -> str:
    """按 id 首字符分片，只允许 a-z0-9 与下划线，其余归到 other。

    分片后单片约 300~500KB，用户点开详情时只读一片。
    """
    text = str(char_id or "").strip().lower()
    head = text[:1]
    if head and (head.isascii() and (head.isalnum() or head == "_")):
        return head
    return "other"


def detail_filename(shard: str) -> str:
    """分片的文件名（单层 json，符合包内文件规范）。"""
    if not shard or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in shard):
        return DETAIL_PREFIX + "other.json"
    return DETAIL_PREFIX + shard + ".json"


def thumb_url_of(trigger: str) -> str:
    """由 trigger 推导缩略图 URL，与源数据 100% 一致。"""
    from urllib.parse import quote

    text = str(trigger or "").replace(":", "_").replace("/", "_")
    return THUMB_BASE + quote(text, safe="()") + ".webp"
