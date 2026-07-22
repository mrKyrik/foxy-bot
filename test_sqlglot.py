import re

query = "INSERT INTO private_voice_settings (user_id, room_name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET room_name=excluded.room_name"

if "ON CONFLICT" in query.upper():
    match = re.search(r'(?is)INSERT\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)\s*ON\s+CONFLICT\s*\((.*?)\)\s*DO\s+UPDATE\s+SET\s+(.*)', query)
    if match:
        table = match.group(1)
        cols = [c.strip() for c in match.group(2).split(',')]
        vals = [v.strip() for v in match.group(3).split(',')]
        conflicts = [c.strip() for c in match.group(4).split(',')]
        updates = match.group(5)
        
        using_cols = []
        for i, (col, val) in enumerate(zip(cols, vals)):
            using_cols.append(f"{val} as {col}")
        using_str = "SELECT " + ", ".join(using_cols) + " FROM DUAL"
        
        on_cond = " AND ".join(f"t.{c} = s.{c}" for c in conflicts)
        
        upd_str = updates.replace("excluded.", "s.")
        
        merge_query = (
            f"MERGE INTO {table} t "
            f"USING ({using_str}) s "
            f"ON ({on_cond}) "
            f"WHEN MATCHED THEN UPDATE SET {upd_str} "
            f"WHEN NOT MATCHED THEN INSERT ({', '.join(cols)}) VALUES ({', '.join('s.'+c for c in cols)})"
        )
        print(merge_query)
