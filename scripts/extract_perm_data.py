#!/usr/bin/env python3
"""Extract perm_mon / perm_obj data from 3eyes binary room files and generate
zone reset SQL statements.

Room binary struct (480-byte header):
  offset   0: char name[80]
  offset  80: short rom_num          (2 bytes, little-endian)
  ...
  offset 212: lasttime perm_mon[10]  (10 x 12 bytes = 120 bytes)
  offset 332: lasttime perm_obj[10]  (10 x 12 bytes = 120 bytes)
  ...

lasttime struct (12 bytes):
  int   interval  (4 bytes, LE)
  int   ltime     (4 bytes, LE)
  short misc      (2 bytes, LE) = VNUM of mob/obj
  2 bytes padding

Output: /tmp/zone_resets.sql with UPDATE statements per zone.
"""

import glob
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

ROOMS_DIR = Path("/home/genos/workspace/3eyes/rooms")
OUTPUT_SQL = Path("/tmp/zone_resets.sql")

HEADER_SIZE = 480
ROM_NUM_OFFSET = 80
PERM_MON_OFFSET = 212
PERM_OBJ_OFFSET = 332
LASTTIME_SIZE = 12
PERM_SLOTS = 10


def parse_lasttime(data: bytes, base_offset: int, index: int) -> tuple:
    """Parse one lasttime struct, return (interval, ltime, misc/vnum)."""
    off = base_offset + index * LASTTIME_SIZE
    interval, ltime, misc = struct.unpack_from("<iih", data, off)
    return interval, ltime, misc


def extract_room(filepath: Path) -> tuple:
    """Extract rom_num, perm_mon resets, and perm_obj resets from a room file.

    Returns (room_vnum, mob_resets, obj_resets).
    """
    with open(filepath, "rb") as f:
        data = f.read(HEADER_SIZE)

    if len(data) < PERM_OBJ_OFFSET + PERM_SLOTS * LASTTIME_SIZE:
        return -1, [], []

    room_vnum = struct.unpack_from("<h", data, ROM_NUM_OFFSET)[0]

    mob_resets = []
    for i in range(PERM_SLOTS):
        _interval, _ltime, misc = parse_lasttime(data, PERM_MON_OFFSET, i)
        if misc > 0:
            mob_resets.append({
                "cmd": "M",
                "arg1": misc,       # mob vnum
                "arg2": 1,          # max count
                "arg3": room_vnum,  # room vnum
            })

    obj_resets = []
    for i in range(PERM_SLOTS):
        _interval, _ltime, misc = parse_lasttime(data, PERM_OBJ_OFFSET, i)
        if misc > 0:
            obj_resets.append({
                "cmd": "O",
                "arg1": misc,       # obj vnum
                "arg2": 0,          # unused
                "arg3": room_vnum,  # room vnum
            })

    return room_vnum, mob_resets, obj_resets


def main() -> None:
    room_files = sorted(glob.glob(str(ROOMS_DIR / "r*" / "r*")))

    if not room_files:
        print(f"ERROR: No room files found in {ROOMS_DIR}", file=sys.stderr)
        sys.exit(1)

    # zone_vnum -> list of reset commands
    zone_resets = defaultdict(list)

    total_rooms = 0
    total_perm_mon = 0
    total_perm_obj = 0
    skipped = 0

    for filepath in room_files:
        room_vnum, mob_resets, obj_resets = extract_room(Path(filepath))
        if room_vnum < 0:
            skipped += 1
            continue

        total_rooms += 1
        total_perm_mon += len(mob_resets)
        total_perm_obj += len(obj_resets)

        zone_vnum = room_vnum // 100
        zone_resets[zone_vnum].extend(mob_resets)
        zone_resets[zone_vnum].extend(obj_resets)

    # Generate SQL
    lines = []
    lines.append("-- Zone reset data extracted from 3eyes binary room perm_mon/perm_obj")
    lines.append(f"-- Total rooms scanned: {total_rooms}")
    lines.append(f"-- Total perm_mon entries: {total_perm_mon}")
    lines.append(f"-- Total perm_obj entries: {total_perm_obj}")
    lines.append(f"-- Zones with data: {len(zone_resets)}")
    lines.append("")
    lines.append("BEGIN;")
    lines.append("")

    for zone_vnum in sorted(zone_resets.keys()):
        resets = zone_resets[zone_vnum]
        # Escape single quotes in JSON (there shouldn't be any, but be safe)
        resets_json = json.dumps(resets, ensure_ascii=False, separators=(",", ":"))
        escaped = resets_json.replace("'", "''")
        lines.append(
            f"UPDATE zones SET resets = '{escaped}' WHERE vnum = {zone_vnum};"
        )

    lines.append("")
    lines.append("COMMIT;")
    lines.append("")

    OUTPUT_SQL.write_text("\n".join(lines), encoding="utf-8")

    # Print statistics
    print("=" * 60)
    print("3eyes perm_mon/perm_obj Extraction Results")
    print("=" * 60)
    print(f"  Rooms directory:      {ROOMS_DIR}")
    print(f"  Total room files:     {len(room_files)}")
    print(f"  Rooms scanned:        {total_rooms}")
    print(f"  Skipped (too small):  {skipped}")
    print(f"  Total perm_mon (M):   {total_perm_mon}")
    print(f"  Total perm_obj (O):   {total_perm_obj}")
    print(f"  Total resets:         {total_perm_mon + total_perm_obj}")
    print(f"  Zones with data:      {len(zone_resets)}")
    print(f"  Output SQL:           {OUTPUT_SQL}")
    print("=" * 60)

    # Show per-zone breakdown
    print("\nPer-zone breakdown:")
    print(f"  {'Zone':>6}  {'Mob(M)':>7}  {'Obj(O)':>7}  {'Total':>7}")
    print(f"  {'----':>6}  {'------':>7}  {'------':>7}  {'-----':>7}")
    for zone_vnum in sorted(zone_resets.keys()):
        resets = zone_resets[zone_vnum]
        mob_count = sum(1 for r in resets if r["cmd"] == "M")
        obj_count = sum(1 for r in resets if r["cmd"] == "O")
        print(f"  {zone_vnum:>6}  {mob_count:>7}  {obj_count:>7}  {len(resets):>7}")

    # Show sample entries
    print("\nSample reset entries (first 15):")
    shown = 0
    for zone_vnum in sorted(zone_resets.keys()):
        for r in zone_resets[zone_vnum]:
            cmd_desc = "Mob" if r["cmd"] == "M" else "Obj"
            print(f"  Zone {zone_vnum:>4}: {cmd_desc} vnum={r['arg1']:>5} -> room {r['arg3']}")
            shown += 1
            if shown >= 15:
                break
        if shown >= 15:
            break


if __name__ == "__main__":
    main()
